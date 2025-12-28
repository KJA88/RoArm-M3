#!/usr/bin/env python3
"""
DEBUG — PIXEL-SPACE VISUAL FOLLOW (GROUND TRUTH)

This script exists ONLY to prove:
- HSV detection works
- Camera orientation is correct
- Robot responds to motion commands correctly

NO homography.
NO table mapping.
NO integration.
"""

import time
import json
import numpy as np
import cv2
import serial
from pathlib import Path
from picamera2 import Picamera2

# ==========================================================
# PATHS
# ==========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HSV_PATH = PROJECT_ROOT / "lessons/03_vision_color_detection/profiles/blue_ball.json"

# ==========================================================
# ROBOT SERIAL
# ==========================================================
SERIAL_PORT = "/dev/ttyUSB0"
BAUD = 115200
SAFE_Z = 120.0

ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.01)
time.sleep(2)

def send_json(payload):
    ser.write((json.dumps(payload) + "\n").encode())

# ==========================================================
# ABSOLUTE TOOL POSITION (SMALL RANGE)
# ==========================================================
tool_x = 0.0
tool_y = 0.0

def move(x, y, z):
    send_json({
        "T": 1041,
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "spd": 80,
        "acc": 80
    })

# ==========================================================
# LOAD HSV
# ==========================================================
with open(HSV_PATH, "r") as f:
    hsv_raw = json.load(f)

HSV_LOWER = np.array(hsv_raw["lower"], dtype=np.uint8)
HSV_UPPER = np.array(hsv_raw["upper"], dtype=np.uint8)
MIN_AREA = hsv_raw.get("min_area", 300)

# ==========================================================
# CAMERA
# ==========================================================
IMG_W, IMG_H = 1280, 720

picam2 = Picamera2()
cfg = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()
time.sleep(0.5)

# ==========================================================
# CONTROL (PIXEL SPACE)
# ==========================================================
PIXEL_DEADBAND = 15
PIXEL_GAIN = 0.05   # mm per pixel
MAX_STEP = 2.0
LOOP_DT = 0.05

# ==========================================================
# VISION
# ==========================================================
def find_center(frame):
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

    return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])

# ==========================================================
# MAIN LOOP
# ==========================================================
print("\n=== PIXEL FOLLOW DEBUG ===")
print("Move the ball LEFT / RIGHT / UP / DOWN")
print("CTRL+C to stop\n")

try:
    while True:
        frame = picam2.capture_array()
        center = find_center(frame)

        if center is None:
            time.sleep(LOOP_DT)
            continue

        u, v = center

        du = u - IMG_W // 2
        dv = v - IMG_H // 2

        if abs(du) < PIXEL_DEADBAND and abs(dv) < PIXEL_DEADBAND:
            time.sleep(LOOP_DT)
            continue

        dx = np.clip(du * PIXEL_GAIN, -MAX_STEP, MAX_STEP)
        dy = np.clip(dv * PIXEL_GAIN, -MAX_STEP, MAX_STEP)

        tool_x += dx
        tool_y += dy

        move(tool_x, tool_y, SAFE_Z)

        time.sleep(LOOP_DT)

except KeyboardInterrupt:
    print("\nStopping")

finally:
    picam2.stop()
    ser.close()
