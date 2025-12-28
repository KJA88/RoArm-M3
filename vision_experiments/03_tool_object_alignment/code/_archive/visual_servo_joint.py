#!/usr/bin/env python3
"""
Joint-Space Visual Servo (BASE + SHOULDER + ELBOW)

- Uses TWO HSV configs:
    - tool_marker.json
    - chess_white.json
- Direct joint-space visual servo (NO IK, NO XYZ)
- Smooth, rate-limited motion
- Starts from SAFE hover pose
"""

import time
import json
import os
import sys
import numpy as np
import cv2
from picamera2 import Picamera2
from roarm_sdk.roarm import roarm

# ==========================================================
# PATHS (ABSOLUTE, VERIFIED)
# ==========================================================
REPO_ROOT = "/home/kallen/RoArm"

HSV_DIR = os.path.join(
    REPO_ROOT, "lessons/03_vision_color_detection/hsv"
)

HSV_TOOL = os.path.join(HSV_DIR, "tool_marker.json")
HSV_OBJ  = os.path.join(HSV_DIR, "chess_white.json")

# ---- Hard fail if files missing ----
for p in (HSV_TOOL, HSV_OBJ):
    if not os.path.exists(p):
        print(f"\n❌ Missing HSV file:\n  {p}")
        print("\nAvailable HSV files:")
        for f in os.listdir(HSV_DIR):
            print(" ", f)
        sys.exit(1)

print("\nUsing HSV files:")
print(" Tool :", HSV_TOOL)
print(" Obj  :", HSV_OBJ)

# ==========================================================
# CAMERA
# ==========================================================
IMG_W, IMG_H = 1280, 720

# ==========================================================
# SERVO PARAMETERS (STABLE)
# ==========================================================
GAIN_BASE     = 0.0025
GAIN_SHOULDER = 0.0020
GAIN_ELBOW    = 0.0020

MAX_STEP = 0.6       # deg / update
DEADZONE = 12        # pixels
DT = 0.05            # 20 Hz loop

# ==========================================================
# SAFE START POSE (HOVER)
# ==========================================================
BASE_START     = 0
SHOULDER_START = 25
ELBOW_START    = 55
WRIST_START    = 0
GRIP_OPEN      = 30

SPEED = 600
ACC   = 50

# ==========================================================
# LOAD HSV
# ==========================================================
def load_hsv(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    return (
        np.array(cfg["lower"]),
        np.array(cfg["upper"]),
        cfg.get("min_area", 300)
    )

tool_min, tool_max, tool_area = load_hsv(HSV_TOOL)
obj_min,  obj_max,  obj_area  = load_hsv(HSV_OBJ)

# ==========================================================
# INIT ARM
# ==========================================================
arm = roarm(
    roarm_type="roarm_m3",
    port="/dev/ttyUSB0",
    baudrate=115200
)

arm.torque_set(1)
arm.move_init()
time.sleep(1)

arm.joint_angle_ctrl(1, BASE_START, SPEED, ACC)
arm.joint_angle_ctrl(2, SHOULDER_START, SPEED, ACC)
arm.joint_angle_ctrl(3, ELBOW_START, SPEED, ACC)
arm.joint_angle_ctrl(4, WRIST_START, SPEED, ACC)
arm.gripper_angle_ctrl(GRIP_OPEN, SPEED, ACC)
time.sleep(1)

base     = BASE_START
shoulder = SHOULDER_START
elbow    = ELBOW_START

print("\n=== JOINT-SPACE VISUAL SERVO (HOVER) ===")
print("Ctrl+C to stop safely")

# ==========================================================
# CAMERA INIT
# ==========================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()

# ==========================================================
# VISION
# ==========================================================
def detect(frame, hmin, hmax, min_area):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, hmin, hmax)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < min_area:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v

# ==========================================================
# MAIN LOOP
# ==========================================================
try:
    while True:
        t0 = time.time()

        frame = picam2.capture_array()

        tool = detect(frame, tool_min, tool_max, tool_area)
        obj  = detect(frame, obj_min,  obj_max,  obj_area)

        if tool is None or obj is None:
            print("Waiting for BOTH tool and object...")
            time.sleep(0.1)
            continue

        ut, vt = tool
        uo, vo = obj

        du = uo - ut
        dv = vo - vt

        print(
            f"tool=({ut:4d},{vt:4d}) "
            f"obj=({uo:4d},{vo:4d}) "
            f"du={du:4d} dv={dv:4d}",
            end=" | "
        )

        if abs(du) < DEADZONE and abs(dv) < DEADZONE:
            print("LOCKED")
            time.sleep(0.05)
            continue

        dB = np.clip(-du * GAIN_BASE,     -MAX_STEP, MAX_STEP)
        dS = np.clip(-dv * GAIN_SHOULDER, -MAX_STEP, MAX_STEP)
        dE = np.clip(-dv * GAIN_ELBOW,    -MAX_STEP, MAX_STEP)

        base     += dB
        shoulder += dS
        elbow    += dE

        arm.joint_angle_ctrl(1, base, SPEED, ACC)
        arm.joint_angle_ctrl(2, shoulder, SPEED, ACC)
        arm.joint_angle_ctrl(3, elbow, SPEED, ACC)

        print(f"dB={dB:+.2f} dS={dS:+.2f} dE={dE:+.2f}")

        elapsed = time.time() - t0
        if elapsed < DT:
            time.sleep(DT - elapsed)

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    picam2.close()
    print("Exited cleanly. Torque still ON.")
