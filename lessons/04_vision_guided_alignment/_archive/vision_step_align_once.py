#!/usr/bin/env python3
"""
Lesson 08 — Vision → Safe Step Alignment (ONE STEP ONLY)

- Headless
- Uses homography from Lesson 07
- Uses HSV from Lesson 07
- Takes ONE camera frame
- Computes XY error
- Moves ONE SMALL SAFE STEP
- Exits immediately
"""

import os
import sys
import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# ============================================================
# IMPORT UV→XY FROM LESSON 07
# ============================================================
sys.path.append(
    os.path.expanduser("~/RoArm/lessons/07_xy_table_mapping")
)
from uv_to_xy_h import uv_to_xy

# ============================================================
# PATHS
# ============================================================
HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping/hsv/red.json"
)

# ============================================================
# SAFETY LIMITS
# ============================================================
MAX_STEP_MM = 5.0     # absolute max per move
DEADZONE_MM = 2.0     # no movement if inside this

# ============================================================
# ROBOT SERIAL
# ============================================================
ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)

def get_robot_xy():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith('{"T":1051'):
            msg = json.loads(line)
            return msg["x"], msg["y"]
    return None

def move_robot_xy(dx, dy):
    cmd = {
        "T": 104,
        "x": dx,
        "y": dy,
        "spd": 400,
        "acc": 50
    }
    ser.write((json.dumps(cmd) + "\n").encode())

# ============================================================
# LOAD HSV
# ============================================================
if not os.path.exists(HSV_PATH):
    print("ERROR: HSV file not found")
    sys.exit(1)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

print("Loaded HSV:")
print("  MIN:", HSV_MIN)
print("  MAX:", HSV_MAX)

# ============================================================
# CAMERA
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()
time.sleep(0.3)

# ============================================================
# CAPTURE FRAME
# ============================================================
frame = picam2.capture_array()
picam2.close()

hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

contours, _ = cv2.findContours(
    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
)

if not contours:
    print("ABORT: No marker detected")
    ser.close()
    sys.exit(0)

c = max(contours, key=cv2.contourArea)
if cv2.contourArea(c) < 300:
    print("ABORT: Marker too small")
    ser.close()
    sys.exit(0)

M = cv2.moments(c)
u = int(M["m10"] / M["m00"])
v = int(M["m01"] / M["m00"])

print(f"Detected marker at u={u}, v={v}")

# ============================================================
# UV → XY
# ============================================================
target_x, target_y = uv_to_xy(u, v)
print(f"Target XY from vision: x={target_x:.1f}, y={target_y:.1f}")

# ============================================================
# ROBOT POSE
# ============================================================
robot_xy = get_robot_xy()
if robot_xy is None:
    print("ABORT: Robot pose unavailable")
    ser.close()
    sys.exit(0)

robot_x, robot_y = robot_xy
print(f"Robot XY: x={robot_x:.1f}, y={robot_y:.1f}")

# ============================================================
# ERROR
# ============================================================
dx = target_x - robot_x
dy = target_y - robot_y

print(f"Error: dx={dx:.1f}, dy={dy:.1f}")

# ============================================================
# DEADZONE
# ============================================================
if abs(dx) < DEADZONE_MM and abs(dy) < DEADZONE_MM:
    print("Inside deadzone — no move")
    ser.close()
    sys.exit(0)

# ============================================================
# CLAMP STEP
# ============================================================
dx = np.clip(dx, -MAX_STEP_MM, MAX_STEP_MM)
dy = np.clip(dy, -MAX_STEP_MM, MAX_STEP_MM)

print(f"STEP MOVE: dx={dx:.1f}, dy={dy:.1f}")

move_robot_xy(dx, dy)
time.sleep(0.5)

print("DONE — one safe step executed")
ser.close()
