#!/usr/bin/env python3
"""
Lesson 03 — HSV Calibration (INTERACTIVE, AUTHORITATIVE)

Human-in-the-loop, headless-safe HSV calibration.

Workflow:
1. Ask user for color / object name
2. Prompt user to center object
3. Capture frame
4. Save annotated image with center box
5. Ask user to confirm centering
6. Retry until confirmed
7. Compute HSV from center patch
8. Save profiles/<name>.json
"""

import json
import os
import numpy as np
import cv2
from picamera2 import Picamera2

# ================= CONFIG =================
PATCH_SIZE = 20      # size of sampling box (pixels)
H_PAD = 10
S_PAD = 40
V_PAD = 40

IMG_W = 1280
IMG_H = 720
CX = IMG_W // 2
CY = IMG_H // 2
# =========================================

# ---------- Paths ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(SCRIPT_DIR, "profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)

IMG_PATH = os.path.join(SCRIPT_DIR, "frame_with_square.jpg")

# ================= USER INPUT =================
print("\nHSV CALIBRATION TOOL")
print("-------------------")

while True:
    name = input("Enter color / object name (filename): ").strip()
    if name:
        break
    print("Name cannot be empty.")

json_path = os.path.join(PROFILES_DIR, f"{name}.json")

print(f"\nHSV profile will be saved as:")
print(f"  {json_path}")

# ================= CAMERA SETUP =================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()

try:
    while True:
        input("\nPlace object at IMAGE CENTER, then press ENTER to capture...")

        # -------- Capture frame --------
        frame = picam2.capture_array()

        # -------- Center patch --------
        half = PATCH_SIZE // 2
        x1, x2 = CX - half, CX + half
        y1, y2 = CY - half, CY + half

        # -------- Annotate image --------
        annotated = frame.copy()
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.drawMarker(
            annotated,
            (CX, CY),
            (255, 0, 0),
            markerType=cv2.MARKER_CROSS,
            markerSize=40,
            thickness=2
        )

        cv2.imwrite(IMG_PATH, annotated)

        print(f"\nSnapshot saved:")
        print(f"  {IMG_PATH}")
        print("Open the image and verify the object is inside the green box.")

        confirm = input("Is the object correctly centered? (y/n): ").strip().lower()

        if confirm != "y":
            print("Recenter the object and try again.")
            continue

        # -------- Compute HSV --------
        patch = frame[y1:y2, x1:x2]
        hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)

        h_vals = hsv_patch[:, :, 0].astype(int)
        s_vals = hsv_patch[:, :, 1].astype(int)
        v_vals = hsv_patch[:, :, 2].astype(int)

        h_min = int(np.min(h_vals) - H_PAD)
        h_max = int(np.max(h_vals) + H_PAD)
        s_min = int(np.min(s_vals) - S_PAD)
        s_max = int(np.max(s_vals) + S_PAD)
        v_min = int(np.min(v_vals) - V_PAD)
        v_max = int(np.max(v_vals) + V_PAD)

        # Clamp to OpenCV ranges
        h_low, h_high = sorted([max(0, min(179, h_min)), max(0, min(179, h_max))])
        s_low, s_high = sorted([max(0, min(255, s_min)), max(0, min(255, s_max))])
        v_low, v_high = sorted([max(0, min(255, v_min)), max(0, min(255, v_max))])

        cfg_out = {
            "lower": [h_low, s_low, v_low],
            "upper": [h_high, s_high, v_high],
            "min_area": 300
        }

        with open(json_path, "w") as f:
            json.dump(cfg_out, f, indent=2)

        print("\nHSV CALIBRATION COMPLETE")
        print(f"Saved HSV:  {json_path}")
        print(f"Lower HSV: {cfg_out['lower']}")
        print(f"Upper HSV: {cfg_out['upper']}")
        break

finally:
    picam2.close()
