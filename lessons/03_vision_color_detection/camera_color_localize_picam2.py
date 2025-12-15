#!/usr/bin/env python3
"""
camera_color_localize_picam2.py

- Capture one frame from Picamera2
- Load HSV range from hsv_config.json (written by inspect_center_hsv.py)
- Detect largest blob of that color
- Print centroid pixel (u, v)
- Save:
  - cam_live_frame.jpg
  - cam_live_mask.jpg
  - cam_live_annotated.jpg
"""

import time
import json
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2

# ---------------- Paths (ROBUST) ----------------

SCRIPT_DIR = Path(__file__).resolve().parent

HSV_CONFIG = SCRIPT_DIR / "hsv_config.json"

IMAGE_RAW  = SCRIPT_DIR / "cam_live_frame.jpg"
IMAGE_MASK = SCRIPT_DIR / "cam_live_mask.jpg"
IMAGE_ANN  = SCRIPT_DIR / "cam_live_annotated.jpg"


# ---------------- HSV Loading ----------------

def load_hsv_range():
    if not HSV_CONFIG.exists():
        raise FileNotFoundError(
            f"{HSV_CONFIG} not found. "
            f"Run camera_snap.py + inspect_center_hsv.py first."
        )

    with HSV_CONFIG.open("r") as f:
        cfg = json.load(f)

    lower = np.array(cfg["lower"], dtype=np.uint8)
    upper = np.array(cfg["upper"], dtype=np.uint8)

    print("Loaded HSV range from:", HSV_CONFIG)
    print("  LOWER_HSV:", lower.tolist())
    print("  UPPER_HSV:", upper.tolist())

    return lower, upper


# ---------------- Main ----------------

def main():
    lower_hsv, upper_hsv = load_hsv_range()

    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)
    picam2.set_controls({"AwbEnable": True})
    picam2.start()
    time.sleep(1.0)

    # capture_array() is OpenCV-compatible in this pipeline
    frame = picam2.capture_array()
    picam2.close()

    print("Captured frame shape:", frame.shape)
    cv2.imwrite(str(IMAGE_RAW), frame)
    print("Saved raw frame to", IMAGE_RAW)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    cv2.imwrite(str(IMAGE_MASK), mask)
    print("Saved mask to", IMAGE_MASK)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print("No contours found — object may be out of view or HSV incorrect.")
        return

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print(f"Largest contour area: {area:.1f} pixels")

    if area < 100:
        print("Largest contour too small (likely noise).")
        return

    M = cv2.moments(largest)
    if M["m00"] == 0:
        print("Cannot compute centroid (m00 = 0).")
        return

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    print(f"Centroid pixel (u, v) = ({cx}, {cy})")

    annotated = frame.copy()
    cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)
    cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2)

    h, w = annotated.shape[:2]
    cv2.drawMarker(
        annotated,
        (w // 2, h // 2),
        (255, 0, 0),
        markerType=cv2.MARKER_CROSS,
        markerSize=20,
        thickness=2,
    )

    cv2.imwrite(str(IMAGE_ANN), annotated)
    print("Saved annotated frame to", IMAGE_ANN)


if __name__ == "__main__":
    main()
