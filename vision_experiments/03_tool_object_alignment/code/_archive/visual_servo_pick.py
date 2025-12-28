#!/usr/bin/env python3
"""
Lesson 06 — Visual Servo Pick (FIXED YAW SIGN + SCALED IBVS)

Phase 1:
- Base yaw alignment (SDK joint control)
- CORRECT sign so yaw converges (no runaway)

Phase 2:
- Image-Based Visual Servoing (IBVS)
- Scaled XY correction from pixel error
- Closed-loop on real XYZ pose
- Guaranteed descent to Z = -90

Camera is mounted 180° rotated relative to arm.
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
from roarm_sdk.roarm import roarm
import subprocess
import os
import sys

# ==========================================================
# USER PARAMETERS
# ==========================================================
Z_PICK   = -90.0
Z_STEP   = 6.0           # mm per iteration
XY_STEP  = 6.0           # max mm per iteration
PIX_TOL  = 10            # pixel deadzone
PIX_FULL = 80            # pixels = full XY_STEP
MIN_AREA = 600

BASE_MIN  = -60
BASE_MAX  =  60
BASE_HOME = 0

SHOULDER_SAFE = 20
ELBOW_SAFE    = 60
WRIST_SAFE    = 0
GRIP_OPEN     = 30

SPEED = 800
ACC   = 50

ROGO = "/home/kallen/RoArm/roarm_simple_move.py"

# ==========================================================
# HSV CONFIG
# ==========================================================
HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv_config.json"
)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

hsv_min = np.array(hsv_cfg["lower"])
hsv_max = np.array(hsv_cfg["upper"])

# ==========================================================
# ARM INIT (SDK — JOINT CONTROL)
# ==========================================================
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

print("=== VISUAL SERVO PICK (FIXED YAW) ===")

# ==========================================================
# CAMERA INIT
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
def detect_object():
    frame = picam2.capture_array()
    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask  = cv2.inRange(hsv, hsv_min, hsv_max)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < MIN_AREA:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v

# ==========================================================
# FIRMWARE IK (same solver as rogo)
# ==========================================================
def ik_move(x, y, z):
    subprocess.run([
        sys.executable, ROGO,
        "goto_xyz",
        f"{x:.1f}",
        f"{y:.1f}",
        f"{z:.1f}",
        "--zmin",
        "-120"
    ], check=True)

# ==========================================================
# PHASE 1 — BASE YAW ALIGNMENT (FIXED SIGN)
# ==========================================================
print("Phase 1: Base yaw alignment")

base_angle = BASE_HOME
last_abs_du = None

while True:
    uv = detect_object()
    if uv is None:
        continue

    u, _ = uv

    # CAMERA IS 180° ROTATED → handled in XY phase
    # YAW SIGN FIX: DO NOT invert du here
    du = (u - 640)

    if last_abs_du is not None and abs(du) > last_abs_du:
        print("Yaw lock (geometry)")
        break

    last_abs_du = abs(du)

    if abs(du) <= PIX_TOL:
        print("Yaw lock (deadzone)")
        break

    step = np.clip(du * 0.05, -3.0, 3.0)
    base_angle = np.clip(base_angle + step, BASE_MIN, BASE_MAX)
    arm.joint_angle_ctrl(1, base_angle, SPEED, ACC)

    time.sleep(0.05)

# ==========================================================
# PHASE 2 — SCALED VISUAL SERVO DESCENT (IBVS)
# ==========================================================
print("Phase 2: Scaled visual servo descent")

x, y, z, *_ = arm.pose_get()

while z > Z_PICK:
    uv = detect_object()
    if uv is None:
        print("Target lost — holding")
        break

    u, v = uv

    # CAMERA 180° ROTATION
    du = -(u - 640)
    dv = -(v - 360)

    pixel_error = np.hypot(du, dv)

    dx = 0.0
    dy = 0.0

    if pixel_error > PIX_TOL:
        scale = min(1.0, pixel_error / PIX_FULL)
        dy = -np.sign(du) * XY_STEP * scale
        dx =  np.sign(dv) * XY_STEP * scale

    z_cmd = max(Z_PICK, z - Z_STEP)

    print(
        f"IMG: du={du:+4d} dv={dv:+4d} | "
        f"px_err={pixel_error:6.1f} | "
        f"WORLD: x={x:+7.1f} y={y:+7.1f} z→{z_cmd:+6.1f}"
    )

    ik_move(x + dx, y + dy, z_cmd)
    time.sleep(0.15)

    x, y, z, *_ = arm.pose_get()

print("DESCENT COMPLETE")

# ==========================================================
# CLEAN EXIT
# ==========================================================
picam2.close()
print("Exited cleanly. Torque still ON.")
