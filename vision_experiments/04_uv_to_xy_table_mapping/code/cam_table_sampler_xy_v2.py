#!/usr/bin/env python3
"""
Lesson 07 — Camera → Table XY Sampler (CLEAN, HEADLESS)

Purpose:
- Detect a colored marker using Lesson 07 HSV
- Read robot XY (read-only)
- Log (u, v, x, y) pairs to CSV
- NO robot motion in this script

Controls:
- ENTER        → log one sample
- q + ENTER    → quit cleanly
"""

import json
import csv
import os
import sys
import select
import time
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# ============================================================
# PATHS (LESSON 07 ONLY — LOCKED)
# ============================================================
BASE_DIR = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping"
)

HSV_PATH = os.path.join(BASE_DIR, "hsv", "red.json")
CSV_PATH = os.path.join(BASE_DIR, "cam_table_samples.csv")

# ============================================================
# ROBOT SERIAL (READ-ONLY)
# ============================================================
ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)

def get_robot_xy():
    """Query robot for current XY position"""
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')

    for _ in range(10):
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith('{"T":1051'):
            try:
                msg = json.loads(line)
                return msg["x"], msg["y"]
            except Exception:
                pass
    return None

# ============================================================
# LOAD HSV (LESSON 07)
# ============================================================
if not os.path.exists(HSV_PATH):
    print("ERROR: HSV file not found:")
    print(HSV_PATH)
    sys.exit(1)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

print("\nLoaded HSV from:")
print(f"  {HSV_PATH}")
print(f"HSV_MIN = {HSV_MIN}")
print(f"HSV_MAX = {HSV_MAX}")

# ============================================================
# CAMERA SETUP
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

IMG_CENTER_X = 640
IMG_CENTER_Y = 360

# ============================================================
# CSV INIT
# ============================================================
new_file = not os.path.exists(CSV_PATH)
csv_file = open(CSV_PATH, "a", newline="")
writer = csv.writer(csv_file)

if new_file:
    writer.writerow(["u", "v", "x", "y"])

print("\n=== LESSON 07 — CAMERA → TABLE XY SAMPLER ===")
print("• Move robot using: robot_keyboard_jog.py")
print("• Move object by hand on table")
print("• ENTER        = log one sample")
print("• q + ENTER    = quit\n")

# ============================================================
# MAIN LOOP
# ============================================================
try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detected = False
        u = v = None

        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 300:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    u = int(M["m10"] / M["m00"])
                    v = int(M["m01"] / M["m00"])
                    detected = True

        # ---- status line ----
        if detected:
            sys.stdout.write(
                f"\rMarker detected at u={u:4d}, v={v:4d}      "
            )
        else:
            sys.stdout.write(
                "\rNo marker detected                          "
            )
        sys.stdout.flush()

        # ---- keyboard handling ----
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip().lower()

            if key == "q":
                print("\nQuit requested")
                break

            elif key == "" and detected:
                xy = get_robot_xy()
                if xy is None:
                    print("\nRobot feedback failed")
                    continue

                x, y = xy
                writer.writerow([u, v, x, y])
                csv_file.flush()

                print(
                    f"\nLOGGED: u={u:4d}, v={v:4d}  ->  x={x:7.1f}, y={y:7.1f}"
                )

        time.sleep(0.03)

except KeyboardInterrupt:
    print("\nKeyboardInterrupt")

finally:
    picam2.close()
    csv_file.close()
    ser.close()
    print("\nExited cleanly.")
