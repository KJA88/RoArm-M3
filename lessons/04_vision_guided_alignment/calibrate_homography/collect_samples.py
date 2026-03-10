#!/usr/bin/env python3
"""
Lesson 04 — Collect UV ↔ XY samples for homography calibration (FIXED)

- Uses robot-reported pose ONLY (T=105)
- Flushes stale serial data
- Waits for fresh pose per sample
- Rejects invalid / repeated feedback
"""

import csv
import json
import time
import serial
import numpy as np
import cv2
from pathlib import Path
from picamera2 import Picamera2

# --------------------------------
# SERIAL / ROBOT CONFIG
# --------------------------------
PORT = "/dev/ttyUSB0"
BAUD = 115200
POSE_TIMEOUT = 1.0  # seconds

# --------------------------------
# PATHS
# --------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
HSV_DIR = PROJECT_ROOT / "lessons/03_vision_color_detection/profiles"
OUT_CSV = Path(__file__).parent / "samples.csv"

# --------------------------------
# SELECT HSV PROFILE
# --------------------------------
profiles = sorted(p.name for p in HSV_DIR.glob("*.json"))
if not profiles:
    raise RuntimeError(f"No HSV profiles found in {HSV_DIR}")

print("\nAvailable HSV profiles:")
for i, name in enumerate(profiles):
    print(f"  [{i}] {name}")

while True:
    try:
        idx = int(input("\nSelect marker HSV profile index: "))
        HSV_PATH = HSV_DIR / profiles[idx]
        break
    except (ValueError, IndexError):
        print("Invalid selection.")

with open(HSV_PATH) as f:
    cfg = json.load(f)

HSV_LOWER = np.array(cfg["lower"], np.uint8)
HSV_UPPER = np.array(cfg["upper"], np.uint8)
MIN_AREA = cfg.get("min_area", 300)

print(f"\nUsing HSV profile: {HSV_PATH.name}")

# --------------------------------
# CAMERA
# --------------------------------
picam2 = Picamera2()
cam_cfg = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cam_cfg)
picam2.start()
time.sleep(0.3)

# --------------------------------
# ROBOT SERIAL
# --------------------------------
ser = serial.Serial(PORT, BAUD, timeout=0.05)
time.sleep(0.3)

def get_fresh_robot_xy():
    """
    Request robot pose and wait for a VALID fresh response.
    """
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')

    start = time.time()
    while time.time() - start < POSE_TIMEOUT:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if "x" in msg and "y" in msg:
                return float(msg["x"]), float(msg["y"])
        except json.JSONDecodeError:
            continue

    return None

def detect_uv(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < MIN_AREA:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v

# --------------------------------
# MAIN LOOP
# --------------------------------
print("\n=== HOMOGRAPHY SAMPLE COLLECTION ===")
print("Jog robot to known XY (Z fixed).")
print("Place marker under tool.")
print("Press ENTER to record.")
print("Ctrl+C to finish.\n")

with open(OUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["u", "v", "x", "y"])

    try:
        while True:
            input("Press ENTER to sample...")

            frame = picam2.capture_array()
            uv = detect_uv(frame)
            if uv is None:
                print("Marker not detected — try again.")
                continue

            xy = get_fresh_robot_xy()
            if xy is None:
                print("Robot pose not received — try again.")
                continue

            u, v = uv
            x, y = xy

            writer.writerow([u, v, x, y])
            print(f"Saved: u={u}, v={v}  ↔  x={x:.2f}, y={y:.2f}")

    except KeyboardInterrupt:
        print("\nSampling complete.")

picam2.stop()
ser.close()
print(f"\nSamples saved to: {OUT_CSV}")
