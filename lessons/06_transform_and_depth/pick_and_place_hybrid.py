#!/usr/bin/env python3
"""
Lesson 06 – Base Yaw Vision Tracking (STABLE)
Headless
Early-stop using image geometry
Graceful terminal quit
NO GUI
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
from roarm_sdk.roarm import roarm
import os
import sys
import select

# ===============================
# SAFE JOINT LIMITS (DEGREES)
# ===============================
BASE_HOME = 0
BASE_MIN  = -60
BASE_MAX  =  60

SHOULDER_SAFE = 20
ELBOW_SAFE    = 60
WRIST_SAFE    = 0
GRIP_OPEN     = 30

SPEED = 800
ACC   = 50

# ===============================
# CONTROL PARAMS
# ===============================
GAIN          = 0.05
MAX_BASE_STEP = 3.0
DEADZONE      = 5

# ===============================
# LOAD HSV CONFIG
# ===============================
HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv_config.json"
)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

hsv_min = np.array(hsv_cfg["lower"])
hsv_max = np.array(hsv_cfg["upper"])

# ===============================
# INIT ARM
# ===============================
arm = roarm(
    roarm_type="roarm_m3",
    port="/dev/ttyUSB0",
    baudrate=115200
)

arm.torque_set(1)
arm.move_init()
time.sleep(1)

arm.joint_angle_ctrl(2, SHOULDER_SAFE, SPEED, ACC)
arm.joint_angle_ctrl(3, ELBOW_SAFE, SPEED, ACC)
arm.joint_angle_ctrl(4, WRIST_SAFE, SPEED, ACC)
arm.gripper_angle_ctrl(GRIP_OPEN, SPEED, ACC)
time.sleep(1)

print("=== BASE YAW TRACKING (STABLE) ===")
print("Type 'q' + Enter to quit safely")

# ===============================
# CAMERA
# ===============================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

# ===============================
# STATE
# ===============================
base_angle = BASE_HOME
hold_base  = False
last_du = None
last_dv = None

# ===============================
# MAIN LOOP
# ===============================
try:
    while True:
        # ---- terminal quit (no GUI) ----
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                print("Quit requested — holding position")
                break

        frame = picam2.capture_array()
        hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask  = cv2.inRange(hsv, hsv_min, hsv_max)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            time.sleep(0.05)
            continue

        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 600:
            time.sleep(0.05)
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            continue

        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        du = u - 640
        dv = v - 360

        # ---- early stop (geometry) ----
        if not hold_base and last_du is not None and last_dv is not None:
            if abs(du) < abs(last_du) and abs(dv) > abs(last_dv):
                print("EARLY STOP — PASSED OBJECT")
                hold_base = True

        last_du = du
        last_dv = dv

        if hold_base or abs(du) <= DEADZONE:
            time.sleep(0.05)
            continue

        step = np.sign(du) * min(MAX_BASE_STEP, abs(du) * GAIN)
        proposed = np.clip(base_angle + step, BASE_MIN, BASE_MAX)

        if proposed != base_angle:
            base_angle = proposed
            arm.joint_angle_ctrl(1, base_angle, SPEED, ACC)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nKeyboardInterrupt — exiting safely")

finally:
    picam2.close()
    print("Exited cleanly. Torque still ON.")
