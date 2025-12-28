#!/usr/bin/env python3
"""
Lesson 04 — Vision-Guided Alignment (AUTHORITATIVE)

Self-contained final vision-guided XY alignment.

- No lesson-to-lesson imports
- No local helper imports
- Consumes HSV JSON from Lesson 03
"""

import time
import json
import numpy as np
import cv2
from pathlib import Path
from picamera2 import Picamera2

# ==========================================================
# PROJECT ROOT (FILES ONLY)
# ==========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ==========================================================
# FILE PATHS (EDIT HSV NAME IF NEEDED)
# ==========================================================
HSV_PATH = (
    PROJECT_ROOT
    / "lessons/03_vision_color_detection/profiles/blue_ball.json"
)

HOMOGRAPHY_PATH = (
    PROJECT_ROOT
    / "lessons/04_vision_guided_alignment/data/homography_matrix_clean.npy"
)

# ==========================================================
# VALIDATION
# ==========================================================
if not HSV_PATH.exists():
    raise FileNotFoundError(f"HSV profile not found: {HSV_PATH}")

if not HOMOGRAPHY_PATH.exists():
    raise FileNotFoundError(f"Homography not found: {HOMOGRAPHY_PATH}")

# ==========================================================
# LOAD HSV CONFIG (INLINE)
# ==========================================================
with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

H = np.load(HOMOGRAPHY_PATH)

# ==========================================================
# CAMERA SETUP
# ==========================================================
IMG_W = 1280
IMG_H = 720

picam2 = Picamera2()
cfg = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()

time.sleep(0.5)

# ==========================================================
# CONTROL PARAMETERS
# ==========================================================
STEP_MM = 3.0
PIXEL_TOL = 12

# ==========================================================
# HELPERS
# ==========================================================
def uv_to_xy(u, v, H):
    pt = np.array([[[u, v]]], dtype=np.float32)
    out = cv2.perspectiveTransform(pt, H)
    return float(out[0, 0, 0]), float(out[0, 0, 1])


def find_object_center(frame, hsv_cfg):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(
        hsv,
        np.array(hsv_cfg["lower"]),
        np.array(hsv_cfg["upper"]),
    )

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < hsv_cfg.get("min_area", 300):
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v


# ==========================================================
# MAIN LOOP
# ==========================================================
print("\n=== LESSON 04: VISION-GUIDED ALIGNMENT ===")
print("CTRL+C to exit\n")

try:
    while True:
        frame = picam2.capture_array()

        center = find_object_center(frame, hsv_cfg)
        if center is None:
            print("Object not detected")
            time.sleep(0.2)
            continue

        u, v = center
        du = u - IMG_W // 2
        dv = v - IMG_H // 2

        print(f"Object UV: ({u}, {v}) | Δ=({du}, {dv})")

        if abs(du) < PIXEL_TOL and abs(dv) < PIXEL_TOL:
            print("✔ Aligned")
            time.sleep(0.4)
            continue

        x_obj, y_obj = uv_to_xy(u, v, H)
        x_ctr, y_ctr = uv_to_xy(IMG_W // 2, IMG_H // 2, H)

        dx = x_obj - x_ctr
        dy = y_obj - y_ctr

        step_x = float(np.clip(dx, -STEP_MM, STEP_MM))
        step_y = float(np.clip(dy, -STEP_MM, STEP_MM))

        print(f"Step XY: ({step_x:.2f}, {step_y:.2f})")

        # ROBOT MOVE COMMAND GOES HERE

        time.sleep(0.3)

except KeyboardInterrupt:
    print("\nExiting")

finally:
    picam2.stop()
