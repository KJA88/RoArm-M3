#!/usr/bin/env python3
"""
Lesson 07 — Vision → XY Step Move (GUARDED)

- ENTER = move once toward detected target
- Z locked
- XY clamped
- Slow speed
- q + ENTER = quit
"""

import json
import os
import sys
import select
import time
import numpy as np
import cv2
from picamera2 import Picamera2
import serial
from uv_to_xy_map import uv_to_xy

# ============================================================
# SAFETY LIMITS
# ============================================================
SAFE_Z = 220.0

X_MIN, X_MAX = 200, 380
Y_MIN, Y_MAX = -120, 120

STEP_GAIN = 0.25      # move 25% of error per step
MAX_STEP = 10.0       # mm

# ============================================================
# PATHS
# ============================================================
BASE_DIR = os.path.expanduser("~/RoArm/lessons/07_xy_table_mapping")
HSV_PATH = os.path.join(BASE_DIR, "hsv", "red.json")

# ============================================================
# LOAD HSV
# ============================================================
with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

# ============================================================
# ROBOT SERIAL
# ============================================================
ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.1)

def get_robot_xy():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith('{"T":1051'):
            msg = json.loads(line)
            return msg["x"], msg["y"]
    return None

def move_robot(x, y):
    cmd = {
        "T": 1041,
        "x": round(float(x), 1),
        "y": round(float(y), 1),
        "z": SAFE_Z,
        "t": 0,
        "r": 0,
        "g": 3.0
    }
    ser.write((json.dumps(cmd) + "\n").encode())

# ============================================================
# CAMERA
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

print("\n=== GUARDED VISION → XY STEP MOVE ===")
print("ENTER = move once toward object")
print("q + ENTER = quit")
print("Z locked at", SAFE_Z)
print()

# ============================================================
# LOOP
# ============================================================
try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            time.sleep(0.05)
            continue

        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 300:
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            continue

        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        target_x, target_y = uv_to_xy(u, v)

        target_x = np.clip(target_x, X_MIN, X_MAX)
        target_y = np.clip(target_y, Y_MIN, Y_MAX)

        pose = get_robot_xy()
        if pose is None:
            continue

        cur_x, cur_y = pose

        dx = target_x - cur_x
        dy = target_y - cur_y

        step_x = np.clip(dx * STEP_GAIN, -MAX_STEP, MAX_STEP)
        step_y = np.clip(dy * STEP_GAIN, -MAX_STEP, MAX_STEP)

        next_x = cur_x + step_x
        next_y = cur_y + step_y

        sys.stdout.write(
            f"\rObject → x={target_x:6.1f}, y={target_y:6.1f} | "
            f"Current → x={cur_x:6.1f}, y={cur_y:6.1f} | "
            f"Next → x={next_x:6.1f}, y={next_y:6.1f}     "
        )
        sys.stdout.flush()

        # ---------- KEYBOARD ----------
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip().lower()

            if key == "q":
                print("\nQuit requested")
                break

            elif key == "":
                print("\nMOVING ONE STEP")
                move_robot(next_x, next_y)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nKeyboardInterrupt")

finally:
    picam2.close()
    ser.close()
    print("\nExited cleanly.")
