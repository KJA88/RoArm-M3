#!/usr/bin/env python3
"""
Lesson 08 — SAFE X-ONLY STEP ALIGNMENT (REFERENCE + SAFETY CORRIDOR)

- Vision-only control
- Reference X captured automatically at startup
- X axis only
- Small bounded steps
- Hard limit on total correction
- Torque enabled
- Headless
- q + ENTER to quit
"""

import json
import time
import os
import sys
import select
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# ============================================================
# PATHS (FROM LESSON 07)
# ============================================================
MAP_DIR = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping"
)

HSV_PATH = os.path.join(MAP_DIR, "hsv", "red.json")
H_PATH   = os.path.join(MAP_DIR, "homography_matrix_clean.npy")

if not os.path.exists(HSV_PATH):
    print("HSV file not found:", HSV_PATH)
    sys.exit(1)

if not os.path.exists(H_PATH):
    print("Homography file not found:", H_PATH)
    sys.exit(1)

# ============================================================
# LOAD HSV
# ============================================================
with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

# ============================================================
# LOAD HOMOGRAPHY
# ============================================================
H = np.load(H_PATH)

def uv_to_xy(u, v):
    p = np.array([u, v, 1.0])
    r = H @ p
    r /= r[2]
    return float(r[0]), float(r[1])

# ============================================================
# ROBOT SERIAL
# ============================================================
ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)

# ENABLE TORQUE (CRITICAL)
ser.write(json.dumps({"T":210,"cmd":1}).encode() + b"\n")
time.sleep(0.5)

def move_x_step(dx_mm):
    cmd = {
        "T": 1041,
        "x": round(dx_mm, 2),
        "y": 0,
        "z": 0,
        "t": 0,
        "r": 0,
        "g": 0
    }
    ser.write((json.dumps(cmd) + "\n").encode())

# ============================================================
# CONTROL PARAMETERS (VERY SAFE)
# ============================================================
GAIN          = 0.25   # vision → mm scaling
MAX_STEP_MM   = 2.0    # max movement per step
DEADZONE_MM   = 2.0    # ignore small noise
MAX_TOTAL_MM  = 10.0   # absolute safety corridor
LOOP_DT       = 0.30   # seconds between steps

# ============================================================
# CAMERA
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

print("\n=== LESSON 08 — SAFE X STEP ALIGNMENT ===")
print("Reference captured automatically at startup")
print("X-axis only")
print("Safety corridor ±{:.1f} mm".format(MAX_TOTAL_MM))
print("q + ENTER to quit safely\n")

# ============================================================
# CAPTURE REFERENCE X (ONCE)
# ============================================================
print("Capturing reference position…")

reference_x = None
while reference_x is None:
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
                reference_x, _ = uv_to_xy(u, v)

    time.sleep(0.1)

print(f"Reference X set to: {reference_x:.2f} mm\n")

# ============================================================
# MAIN LOOP
# ============================================================
try:
    while True:

        # -------- QUIT --------
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                print("Quit requested")
                break

        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            print("No marker detected")
            time.sleep(LOOP_DT)
            continue

        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 300:
            time.sleep(LOOP_DT)
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            time.sleep(LOOP_DT)
            continue

        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        current_x, _ = uv_to_xy(u, v)

        # -------- REFERENCE-BASED ERROR --------
        error_x = current_x - reference_x

        print(f"Vision X error: {error_x:7.2f} mm")

        if abs(error_x) < DEADZONE_MM:
            time.sleep(LOOP_DT)
            continue

        if abs(error_x) > MAX_TOTAL_MM:
            print("⚠️  Error exceeds safe range — holding position")
            time.sleep(LOOP_DT)
            continue

        step = np.clip(error_x * GAIN, -MAX_STEP_MM, MAX_STEP_MM)

        move_x_step(step)
        time.sleep(LOOP_DT)

except KeyboardInterrupt:
    print("\nCtrl+C")

finally:
    picam2.close()
    ser.close()
    print("Exited cleanly")
