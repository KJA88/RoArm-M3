#!/usr/bin/env python3
"""
Lesson 05 — Vision-Guided Continuous Tracking (AUTHORITATIVE)

- Continuous visual servoing (XY)
- Uses T=1041 streaming
- Torque-safe
- Headless
- Terminal quit support
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial
import sys
import select
from pathlib import Path

# =========================================================
# TUNING & SAFETY
# =========================================================
GAIN      = 0.28
MAX_STEP  = 10.0
PIX_TOL   = 1
DT        = 0.03

TARGET_U  = 640
TARGET_V  = 360

MIN_X, MAX_X = 200, 380
MIN_Y, MAX_Y = -150, 150
SAFE_Z       = 260

GRIPPER_SAFE = 3.0
ROBOT_PORT   = "/dev/ttyUSB0"
BAUD         = 115200

# =========================================================
# HSV CONFIG (AUTHORITATIVE LOCATION)
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HSV_PATH = PROJECT_ROOT / "lessons/03_vision_color_detection/hsv/tool_marker.json"

if not HSV_PATH.exists():
    raise FileNotFoundError(f"HSV config not found: {HSV_PATH}")

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

# =========================================================
# CAMERA
# =========================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

# =========================================================
# SERIAL
# =========================================================
ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.05)

def get_actual_xy():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors='ignore').strip()
        if line.startswith('{"T":1051'):
            try:
                msg = json.loads(line)
                return msg["x"], msg["y"]
            except:
                pass
    return None

def move_stream(x, y, z):
    cmd = {
        "T": 1041,
        "x": round(float(np.clip(x, MIN_X, MAX_X)), 1),
        "y": round(float(np.clip(y, MIN_Y, MAX_Y)), 1),
        "z": round(float(z), 1),
        "t": 0,
        "r": 0,
        "g": GRIPPER_SAFE
    }
    ser.write((json.dumps(cmd) + "\n").encode())

# =========================================================
# STARTUP
# =========================================================
print("\n=== Lesson 05: Vision-Guided Tracking ===")
print("Type 'q' + Enter to quit | Ctrl+C also safe")

# Torque ON
ser.write(json.dumps({"T": 210, "cmd": 1}).encode() + b"\n")

fb = get_actual_xy()
if fb is None:
    print("CRITICAL: Robot feedback failed")
    exit()

v_x, v_y = fb
move_stream(v_x, v_y, SAFE_Z)

# =========================================================
# MAIN LOOP
# =========================================================
try:
    while True:
        # ---- terminal quit ----
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                print("Quit requested — holding position")
                break

        t0 = time.time()

        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

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

        dt = time.time() - t0
        if dt < DT:
            time.sleep(DT - dt)

except KeyboardInterrupt:
    print("\nCtrl+C — stopping safely")

finally:
    picam2.close()
    ser.close()
    print("Exited cleanly. Torque remains ON.")
