#!/usr/bin/env python3
"""
MAX-SMOOTH Relative Visual Servo (XY only, SAFE START)

This is the smoothest achievable behavior using firmware XYZ position commands.

Techniques used:
- Safe start pose
- Locked Z
- Frame averaging (vision low-pass)
- Low command rate (~10 Hz)
- Gain scheduling
- Large deadzone near target

Beyond this, velocity control is required.
"""

import json
import time
import serial
from pathlib import Path
from collections import deque

import numpy as np
import cv2
from picamera2 import Picamera2

# ==========================================================
# SAFE START
# ==========================================================
START_X = 200.0
START_Y = 0.0
START_Z = 100.0

# ==========================================================
# PATHS
# ==========================================================
REPO_ROOT = Path.home() / "RoArm"
HSV_DIR = REPO_ROOT / "lessons/03_vision_color_detection/hsv"

TOOL_HSV = HSV_DIR / "tool_marker.json"
OBJ_HSV  = HSV_DIR / "chess_white.json"

# ==========================================================
# LOAD HSV
# ==========================================================
def load_hsv(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    return np.array(cfg["lower"]), np.array(cfg["upper"]), cfg.get("min_area", 300)

tool_min, tool_max, tool_area = load_hsv(TOOL_HSV)
obj_min,  obj_max,  obj_area  = load_hsv(OBJ_HSV)

# ==========================================================
# ROBOT SERIAL
# ==========================================================
ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.05)

def move_xyz(x, y, z):
    ser.write((json.dumps({
        "T": 1041,
        "x": round(x, 1),
        "y": round(y, 1),
        "z": round(z, 1),
        "t": 0,
        "r": 0,
        "g": 3.0
    }) + "\n").encode())

# ==========================================================
# CAMERA
# ==========================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

# ==========================================================
# VISION
# ==========================================================
def detect(hsv, lo, hi, min_area):
    mask = cv2.inRange(hsv, lo, hi)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < min_area:
        return None
    M = cv2.moments(c)
    if M["m00"] == 0:
        return None
    return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])

# ==========================================================
# SERVO PARAMETERS
# ==========================================================
GAIN_FAR  = 0.006
GAIN_NEAR = 0.002

MAX_STEP = 5.0
DEADZONE = 10

# Average over last N frames
AVG_N = 5
du_hist = deque(maxlen=AVG_N)
dv_hist = deque(maxlen=AVG_N)

# ==========================================================
# START
# ==========================================================
print("Moving to safe start...")
move_xyz(START_X, START_Y, START_Z)
time.sleep(3.0)

x_cmd, y_cmd, z_cmd = START_X, START_Y, START_Z
print("Visual servo started (max smooth mode)\n")

# ==========================================================
# MAIN LOOP (LOW RATE)
# ==========================================================
try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        tool = detect(hsv, tool_min, tool_max, tool_area)
        obj  = detect(hsv, obj_min,  obj_max,  obj_area)

        if tool is None or obj is None:
            time.sleep(0.1)
            continue

        u_t, v_t = tool
        u_o, v_o = obj

        # Camera rotated 180°
        du_hist.append(-(u_o - u_t))
        dv_hist.append(-(v_o - v_t))

        du = np.mean(du_hist)
        dv = np.mean(dv_hist)

        if abs(du) < DEADZONE and abs(dv) < DEADZONE:
            time.sleep(0.15)
            continue

        err = max(abs(du), abs(dv))
        gain = GAIN_FAR if err > 80 else GAIN_NEAR

        dx = np.clip(-dv * gain, -MAX_STEP, MAX_STEP)
        dy = np.clip(-du * gain, -MAX_STEP, MAX_STEP)

        x_cmd += dx
        y_cmd += dy

        move_xyz(x_cmd, y_cmd, z_cmd)

        print(f"du={du:6.1f} dv={dv:6.1f} → dx={dx:+.2f} dy={dy:+.2f}")

        # IMPORTANT: slow update rate
        time.sleep(0.12)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    picam2.close()
    ser.close()
