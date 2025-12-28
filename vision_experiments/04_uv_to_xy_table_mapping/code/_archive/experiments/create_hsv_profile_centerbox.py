#!/usr/bin/env python3
"""
HSV Calibration with Center Box (HEADLESS, ITERATIVE)

Workflow:
1. Ask for color name
2. ENTER → take preview snapshot with 20x20 center box
3. User manually centers object
4. ENTER → take NEW preview (overwrites previous)
5. Ask: is object centered?
6. If no → repeat
7. If yes → take FINAL snapshot
8. Compute HSV from center box
9. Save HSV JSON to Lesson 7 folder
"""

import os
import json
import cv2
import numpy as np
from picamera2 import Picamera2
from pathlib import Path

# ===============================
# PATHS (LESSON 7 ONLY)
# ===============================
BASE_DIR = Path.home() / "RoArm/lessons/07_xy_table_mapping"
HSV_DIR  = BASE_DIR / "hsv"
CAL_DIR  = BASE_DIR / "hsv_calibration"

HSV_DIR.mkdir(exist_ok=True)
CAL_DIR.mkdir(exist_ok=True)

PREVIEW_PATH = CAL_DIR / "snapshot_preview.jpg"
FINAL_PATH   = CAL_DIR / "snapshot_final.jpg"

# ===============================
# CONFIG
# ===============================
BOX_HALF = 10  # 20x20 box
H_MARGIN = 10
S_MARGIN = 40
V_MARGIN = 40

# ===============================
# CAMERA
# ===============================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

# ===============================
# INPUT COLOR NAME
# ===============================
color_name = input("Enter color name (e.g. tool_marker): ").strip()
if not color_name:
    raise RuntimeError("Color name cannot be empty.")

HSV_JSON_PATH = HSV_DIR / f"{color_name}.json"

print("\n--- HSV CALIBRATION STARTED ---")
print("Images will be written here:")
print(f"  {PREVIEW_PATH}")
print(f"  {FINAL_PATH}")
print()

# ===============================
# MAIN LOOP
# ===============================
while True:
    input("Press ENTER to capture preview...")

    frame = picam2.capture_array()
    h, w, _ = frame.shape
    cx, cy = w // 2, h // 2

    preview = frame.copy()
    cv2.rectangle(
        preview,
        (cx - BOX_HALF, cy - BOX_HALF),
        (cx + BOX_HALF, cy + BOX_HALF),
        (0, 0, 255),
        2
    )

    cv2.imwrite(str(PREVIEW_PATH), preview)
    print(f"Preview updated: {PREVIEW_PATH}")
    print("Open the image and manually center the object in the box.")

    ans = input("Is the item centered in the box? (y/n): ").strip().lower()
    if ans == "y":
        break

# ===============================
# FINAL CAPTURE
# ===============================
final = picam2.capture_array()
cv2.imwrite(str(FINAL_PATH), final)
print(f"\nFinal snapshot saved: {FINAL_PATH}")

# ===============================
# HSV COMPUTATION
# ===============================
hsv = cv2.cvtColor(final, cv2.COLOR_BGR2HSV)

roi = hsv[
    cy - BOX_HALF : cy + BOX_HALF,
    cx - BOX_HALF : cx + BOX_HALF
]

h_vals = roi[:, :, 0]
s_vals = roi[:, :, 1]
v_vals = roi[:, :, 2]

h_min, h_max = int(h_vals.min()), int(h_vals.max())
s_min, s_max = int(s_vals.min()), int(s_vals.max())
v_min, v_max = int(v_vals.min()), int(v_vals.max())

lower = [
    max(0,   h_min - H_MARGIN),
    max(0,   s_min - S_MARGIN),
    max(0,   v_min - V_MARGIN),
]
upper = [
    min(179, h_max + H_MARGIN),
    min(255, s_max + S_MARGIN),
    min(255, v_max + V_MARGIN),
]

# ===============================
# SAVE HSV FILE
# ===============================
with open(HSV_JSON_PATH, "w") as f:
    json.dump(
        {"lower": lower, "upper": upper},
        f,
        indent=2
    )

print("\n--- HSV CALIBRATION COMPLETE ---")
print(f"Saved HSV profile: {HSV_JSON_PATH}")
print(f"Lower: {lower}")
print(f"Upper: {upper}")

picam2.close()
