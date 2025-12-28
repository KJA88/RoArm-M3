#!/usr/bin/env python3
"""
Vision-driven absolute XY tracking
MATCHES circle/helix demo behavior exactly.

Key rules:
- Absolute XYZ only
- Z locked
- t, r locked
- g locked
- No deltas
"""

import time, json, math
import numpy as np
import cv2
import serial
from pathlib import Path
from picamera2 import Picamera2

# -------------------------------
# SERIAL / ROBOT CONFIG
# -------------------------------
PORT = "/dev/ttyUSB0"
BAUD = 115200

Z_LOCK = 100.0
T_LOCK = 0.0
R_LOCK = 0.0
G_LOCK = 3.0     # same as your demo
DT = 0.04        # ~25 Hz (same feel)

# Workspace clamp (keep it sane)
X_MIN, X_MAX = 150.0, 350.0
Y_MIN, Y_MAX = -150.0, 150.0

# -------------------------------
# PATHS (YOUR FILES)
# -------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HSV_PATH = PROJECT_ROOT / "lessons/03_vision_color_detection/profiles/green_triangle.json"
H_PATH   = PROJECT_ROOT / "lessons/04_vision_guided_alignment/data/homography_matrix_clean.npy"

# -------------------------------
# UART helper
# -------------------------------
def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))

# -------------------------------
# CAMERA
# -------------------------------
IMG_W, IMG_H = 1280, 720

picam2 = Picamera2()
cfg = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()
time.sleep(0.3)

# -------------------------------
# LOAD HSV + HOMOGRAPHY
# -------------------------------
with open(HSV_PATH) as f:
    hsv = json.load(f)

HSV_LOWER = np.array(hsv["lower"], np.uint8)
HSV_UPPER = np.array(hsv["upper"], np.uint8)
MIN_AREA  = hsv.get("min_area", 300)

H = np.load(H_PATH)

def uv_to_xy(u, v):
    pt = np.array([[[u, v]]], np.float32)
    out = cv2.perspectiveTransform(pt, H)
    return float(out[0,0,0]), float(out[0,0,1])

# -------------------------------
# VISION
# -------------------------------
def find_ball(frame):
    hsv_img = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv_img, HSV_LOWER, HSV_UPPER)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < MIN_AREA:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    return int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])

# -------------------------------
# MAIN
# -------------------------------
def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.05)
    time.sleep(0.5)

    # Torque ON
    send(ser, {"T":210, "cmd":1})
    time.sleep(0.2)

    print("\n=== VISION TRACKING (CIRCLE-SCRIPT STYLE) ===")
    print("Z locked, orientation locked, absolute XYZ\n")

    try:
        while True:
            frame = picam2.capture_array()
            ball = find_ball(frame)

            if ball is None:
                time.sleep(DT)
                continue

            u, v = ball
            x, y = uv_to_xy(u, v)

            # Clamp like a path generator would
            x = max(X_MIN, min(X_MAX, x))
            y = max(Y_MIN, min(Y_MAX, y))

            # EXACT SAME STRUCTURE AS CIRCLE DEMO
            send(ser, {
                "T": 1041,
                "x": x,
                "y": y,
                "z": Z_LOCK,
                "t": T_LOCK,
                "r": R_LOCK,
                "g": G_LOCK,
            })

            time.sleep(DT)

    except KeyboardInterrupt:
        print("\nStopping")

    finally:
        picam2.stop()
        ser.close()

if __name__ == "__main__":
    main()
