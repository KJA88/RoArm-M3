#!/usr/bin/env python3
"""
Lesson 05 Final Capstone — Virtual Pose Tracker
HIGH-ACCURACY VERSION (TORQUE SAFE + TERMINAL QUIT)
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial
import os
import sys
import select

# =========================================================
# 1. TUNING & SAFETY FENCING
# =========================================================
GAIN         = 0.28
MAX_STEP     = 10.0
PIX_TOL      = 1
DT           = 0.03

TARGET_U     = 640
TARGET_V     = 360

MIN_X, MAX_X = 200, 380
MIN_Y, MAX_Y = -150, 150
SAFE_Z       = 260  

GRIPPER_SAFE = 3.0      
ROBOT_PORT   = "/dev/ttyUSB0"
BAUD         = 115200
HSV_CONFIG_PATH = "lessons/03_vision_color_detection/hsv_config.json"

# =========================================================
# 2. CORE FUNCTIONS
# =========================================================

def load_hsv_config():
    if not os.path.exists(HSV_CONFIG_PATH):
        print(f"CRITICAL: {HSV_CONFIG_PATH} not found.")
        return None, None
    with open(HSV_CONFIG_PATH, 'r') as f:
        data = json.load(f)
    try:
        return np.array(data['lower']), np.array(data['upper'])
    except KeyError:
        return None, None

picam2 = Picamera2()
config = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(config)
picam2.start()

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.05)

def get_actual_pos():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors='ignore').strip()
        if line.startswith('{"T":1051'):
            try:
                msg = json.loads(line)
                return msg["x"], msg["y"]
            except:
                continue
    return None

def move_stream(x, y, z):
    tx = np.clip(x, MIN_X, MAX_X)
    ty = np.clip(y, MIN_Y, MAX_Y)
    cmd = {
        "T": 1041,
        "x": round(float(tx), 1),
        "y": round(float(ty), 1),
        "z": round(float(z), 1),
        "t": 0,
        "r": 0,
        "g": GRIPPER_SAFE
    }
    ser.write((json.dumps(cmd) + "\n").encode())

# =========================================================
# 3. MAIN EXECUTION
# =========================================================
print("\n=== Lesson 05: High-Accuracy Tracker (SAFE) ===")
print("Type 'q' + Enter to quit | Ctrl+C also safe")

hsv_min, hsv_max = load_hsv_config()
if hsv_min is None:
    exit()

# TORQUE ON
ser.write(json.dumps({"T": 210, "cmd": 1}).encode() + b"\n")

fb = get_actual_pos()
if fb:
    v_x, v_y = fb
    move_stream(v_x, v_y, SAFE_Z)
else:
    print("CRITICAL: Robot offline.")
    exit()

# =========================================================
# MAIN LOOP
# =========================================================
try:
    while True:
        # ---------- TERMINAL QUIT ----------
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                print("Quit requested — holding position")
                break

        loop_start = time.time()
        frame = picam2.capture_array()
        
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_frame, hsv_min, hsv_max)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 300:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    u = int(M["m10"] / M["m00"])
                    v = int(M["m01"] / M["m00"])
                    
                    du = u - TARGET_U
                    dv = v - TARGET_V
                    
                    if abs(du) > PIX_TOL or abs(dv) > PIX_TOL:
                        dx = np.clip(dv * GAIN, -MAX_STEP, MAX_STEP)
                        dy = np.clip(du * GAIN, -MAX_STEP, MAX_STEP)
                        v_x += dx
                        v_y += dy
                        move_stream(v_x, v_y, SAFE_Z)
        
        elapsed = time.time() - loop_start
        if elapsed < DT:
            time.sleep(DT - elapsed)

except KeyboardInterrupt:
    print("\nCtrl+C — stopping loop safely")

finally:
    picam2.close()
    ser.close()
    print("Exited cleanly. Torque remains ON.")
