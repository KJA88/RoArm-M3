#!/usr/bin/env python3
"""
Lesson 06 — Geometry-Aware XY Alignment → Single IK Descent (FINAL)

• Vision aligns X/Y using BASE YAW ONLY
• Early-stop geometry (no oscillation)
• Holds position
• ONE raw IK move using firmware (T=102)
• Negative Z allowed
• Same execution path as `rogo`
• NO SDK pose_ctrl
• NO Cartesian mode
• Torque-safe
"""

import time
import json
import cv2
import numpy as np
import serial
import os
import sys
import select
from picamera2 import Picamera2

# ===============================
# SERIAL CONFIG
# ===============================
PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(0.3)

def send(cmd):
    msg = json.dumps(cmd)
    ser.write((msg + "\n").encode())
    print("→", msg)

# ===============================
# USER TARGET (FIXED Z)
# ===============================
Z_PICK = -90.0     # SAFE NEGATIVE Z
SPEED  = 100
ACC    = 50

# ===============================
# BASE YAW LIMITS (DEGREES)
# ===============================
BASE_MIN = -60
BASE_MAX =  60
BASE_HOME = 0

# ===============================
# VISION CONTROL
# ===============================
GAIN          = 0.05
MAX_BASE_STEP = 3.0
DEADZONE      = 6

# ===============================
# HSV CONFIG
# ===============================
HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv_config.json"
)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

hsv_min = np.array(hsv_cfg["lower"])
hsv_max = np.array(hsv_cfg["upper"])

# ===============================
# TORQUE ON
# ===============================
print("Torque ON")
send({"T":210,"cmd":1})
time.sleep(0.3)

# ===============================
# SAFE INIT POSE (NO CANDLE)
# ===============================
print("Move to safe init")
send({
    "T":102,
    "base":0,
    "shoulder":0,
    "elbow":1.5708,
    "wrist":0,
    "roll":0,
    "hand":3.141592653589793,
    "spd":SPEED,
    "acc":ACC
})
time.sleep(2)

# ===============================
# CAMERA SETUP
# ===============================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format":"RGB888","size":(1280,720)}
)
picam2.configure(cfg)
picam2.start()

print("\n=== XY ALIGN → IK DESCEND ===")
print("q + Enter or Ctrl+C to exit safely")

# ===============================
# STATE
# ===============================
base_angle = BASE_HOME
hold_base  = False
last_du    = None
last_dv    = None

# ===============================
# XY ALIGN LOOP
# ===============================
try:
    while True:
        # ---- keyboard quit ----
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                print("Quit requested — holding")
                sys.exit(0)

        frame = picam2.capture_array()
        hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask  = cv2.inRange(hsv, hsv_min, hsv_max)

        contours,_ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPRO_SIMPLE
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

        # ---- early-stop geometry ----
        if not hold_base and last_du is not None and last_dv is not None:
            if abs(du) < abs(last_du) and abs(dv) > abs(last_dv):
                print("ALIGNMENT LOCKED (GEOMETRY)")
                hold_base = True
                break

        last_du = du
        last_dv = dv

        if abs(du) <= DEADZONE:
            print("ALIGNMENT LOCKED (DEADZONE)")
            break

        step = np.sign(du) * min(MAX_BASE_STEP, abs(du) * GAIN)
        proposed = np.clip(base_angle + step, BASE_MIN, BASE_MAX)

        if proposed != base_angle:
            base_angle = proposed
            send({
                "T":121,
                "joint":1,
                "angle":base_angle,
                "spd":70,
                "acc":20
            })

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nInterrupted — holding")

# ===============================
# READ CURRENT POSE
# ===============================
send({"T":105})
time.sleep(0.3)

raw = ser.readline().decode(errors="ignore").strip()
pose = json.loads(raw)

x = pose["x"]
y = pose["y"]

print("\nDESCENT START (RAW IK)")
print(f"Current XY = ({x:.1f}, {y:.1f})  Target Z = {Z_PICK}")

# ===============================
# SINGLE IK MOVE (LIKE rogo)
# ===============================
send({
    "T":102,
    "x":x,
    "y":y,
    "z":Z_PICK,
    "spd":SPEED,
    "acc":ACC
})

print("DESCENT COMPLETE — HOLDING")
print("Ctrl+C to exit (torque stays ON)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExit — torque remains ON")
    picam2.close()
    ser.close()
