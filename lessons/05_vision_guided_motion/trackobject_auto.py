#!/usr/bin/env python3
"""
Lesson 05 Final Capstone — Virtual Pose Tracker
Optimized for Lighting Stability and "Settling" Accuracy.
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# =========================================================
# 1. TUNING & SAFETY FENCING
# =========================================================
GAIN         = 0.15     
MAX_STEP     = 6.0      
PIX_TOL      = 4        
DT           = 0.05     
STABLE_REQ   = 3        

# HARDWARE FENCE
MIN_X, MAX_X = 200, 380
MIN_Y, MAX_Y = -150, 150
SAFE_Z       = 260  

GRIPPER_SAFE = 3.0      
ROBOT_PORT   = "/dev/ttyUSB0"
BAUD         = 115200

# =========================================================
# 2. CORE FUNCTIONS
# =========================================================
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"format": "RGB888", "size": (1280, 720)})
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
            except: continue
    return None

def move_stream(x, y, z):
    tx = np.clip(x, MIN_X, MAX_X)
    ty = np.clip(y, MIN_Y, MAX_Y)
    cmd = {"T": 1041, "x": round(float(tx), 1), "y": round(float(ty), 1), 
           "z": round(float(z), 1), "t": 0, "r": 0, "g": GRIPPER_SAFE}
    ser.write((json.dumps(cmd) + "\n").encode())

# =========================================================
# 3. MAIN EXECUTION
# =========================================================
print("\n=== Lesson 05: Final Stable Tracker ===")
ser.write(json.dumps({"T": 210, "cmd": 1}).encode() + b"\n")

fb = get_actual_pos()
if fb:
    v_x, v_y = fb
    move_stream(v_x, v_y, SAFE_Z)
else:
    print("CRITICAL: Robot offline.")
    exit()

stable_frames = 0

try:
    while True:
        loop_start = time.time()
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 50, 50]), np.array([85, 255, 255]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 400:
                stable_frames += 1
                if stable_frames >= STABLE_REQ:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        u, v = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                        du, dv = u - 640, v - 360 
                        
                        if abs(du) > PIX_TOL or abs(dv) > PIX_TOL:
                            dx = np.clip(dv * GAIN, -MAX_STEP, MAX_STEP)
                            dy = np.clip(du * GAIN, -MAX_STEP, MAX_STEP)
                            v_x += dx
                            v_y += dy
                            move_stream(v_x, v_y, SAFE_Z)
                        else:
                            # Re-sync periodically while centered
                            fb = get_actual_pos()
                            if fb: v_x, v_y = fb
        else:
            stable_frames = 0

        elapsed = time.time() - loop_start
        if elapsed < DT:
            time.sleep(DT - elapsed)

except KeyboardInterrupt:
    ser.write(json.dumps({"T": 210, "cmd": 0}).encode() + b"\n")
finally:
    ser.close()
    picam2.close()