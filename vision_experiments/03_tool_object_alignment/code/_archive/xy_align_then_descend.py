#!/usr/bin/env python3
import sys
import time
import math
import subprocess
import cv2
import numpy as np

# ---------------- CONFIG ----------------
ROARM_BIN = "/home/kallen/RoArm/roarm_simple_move.py"
CAM_INDEX = 0

IMG_W = 1280
IMG_H = 720
CX = IMG_W // 2
CY = IMG_H // 2

# visual gains (KEEP SMALL)
K_YAW = 0.03        # rad per normalized pixel
K_XY  = 0.4         # mm per normalized pixel
MAX_BASE_STEP = math.radians(3)

TARGET_Z = -90      # wrist pitch (deg)

# stop conditions
PIX_TOL = 12
MAX_ITERS = 60

# ----------------------------------------


def roarm_joint(joint, angle_deg, spd=70):
    subprocess.run([
        sys.executable, ROARM_BIN,
        "joint", str(joint),
        str(angle_deg),
        "--spd", str(spd)
    ], check=True)


def roarm_goto(x, y, z):
    subprocess.run([
        sys.executable, ROARM_BIN,
        "goto", str(x), str(y), str(z),
        "--settle", "0.2"
    ], check=True)


def get_arm_xyz():
    p = subprocess.run(
        [sys.executable, ROARM_BIN, "pose"],
        capture_output=True, text=True
    )
    for line in p.stdout.splitlines():
        if line.strip().startswith("{"):
            import json
            j = json.loads(line)
            return j["x"], j["y"], j["z"]
    raise RuntimeError("Pose not found")


def find_object(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # BASIC RED (adjust later)
    lower = np.array([0, 120, 80])
    upper = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v


# ---------------- MAIN -------------------

def main():
    print("\n=== VISUAL SERVO PICK (CORRECTED) ===")

    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_H)

    # neutral pose
    roarm_joint(1, 0)
    roarm_joint(2, 20)
    roarm_joint(3, 60)
    roarm_joint(4, 0)
    roarm_joint(6, 150)

    time.sleep(1.0)

    for i in range(MAX_ITERS):
        ret, frame = cap.read()
        if not ret:
            continue

        obj = find_object(frame)
        if obj is None:
            print("No object")
            continue

        u, v = obj

        du = u - CX
        dv = v - CY

        print(f"[{i}] pixel err: du={du} dv={dv}")

        if abs(du) < PIX_TOL and abs(dv) < PIX_TOL:
            print("✓ CENTERED")
            break

        # -------- CAMERA IS 180° ROTATED --------
        du = -du
        dv = -dv

        # -------- YAW (BASE) --------
        yaw_step = np.clip(-K_YAW * du, -MAX_BASE_STEP, MAX_BASE_STEP)
        yaw_deg = math.degrees(yaw_step)
        roarm_joint(1, yaw_deg)

        # -------- PLANAR XY CORRECTION --------
        x, y, z = get_arm_xyz()

        dx = -K_XY * dv
        dy =  K_XY * dv

        roarm_goto(x + dx, y + dy, z)

        time.sleep(0.15)

    print("Descending...")

    # FORCE TOOL ORIENTATION
    roarm_joint(4, TARGET_Z)

    x, y, z = get_arm_xyz()
    roarm_goto(x, y, z - 80)

    print("DONE")


if __name__ == "__main__":
    main()
