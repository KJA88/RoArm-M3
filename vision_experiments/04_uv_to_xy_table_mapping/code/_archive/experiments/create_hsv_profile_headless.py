#!/usr/bin/env python3
"""
Lesson 07 — Headless HSV Profile Creator

Creates ONE HSV file for table mapping.
No GUI. Everything saved inside lesson 07.
"""

import cv2
import json
import os
import numpy as np
from picamera2 import Picamera2

# ============================================================
# PATHS (LESSON 07)
# ============================================================
BASE_DIR = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping"
)

HSV_DIR = os.path.join(BASE_DIR, "hsv")
CAL_DIR = os.path.join(BASE_DIR, "hsv_calibration")

RAW_IMG = os.path.join(CAL_DIR, "snapshot_raw.jpg")
ROI_IMG = os.path.join(CAL_DIR, "snapshot_roi.jpg")

os.makedirs(HSV_DIR, exist_ok=True)
os.makedirs(CAL_DIR, exist_ok=True)

# ============================================================
# HSV MARGINS
# ============================================================
H_MARGIN = 10
S_MARGIN = 40
V_MARGIN = 40

# ============================================================
# OBJECT NAME
# ============================================================
name = input("Enter object/color name (e.g. tool_marker): ").strip()
if not name:
    print("ERROR: name cannot be empty")
    exit(1)

HSV_PATH = os.path.join(HSV_DIR, f"{name}.json")

# ============================================================
# CAMERA SNAPSHOT
# ============================================================
picam2 = Picamera2()
picam2.configure(
    picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
)
picam2.start()
frame = picam2.capture_array()
picam2.close()

cv2.imwrite(RAW_IMG, frame)
print(f"\nSaved snapshot: {RAW_IMG}")
print("OPEN THIS IMAGE to find the marker.\n")

# ============================================================
# REGION INPUT
# ============================================================
print("Enter region containing ONLY the marker.")
print("Format: x y width height")
print("Example: 600 340 80 80\n")

try:
    x, y, w, h = map(int, input("Region: ").split())
except Exception:
    print("ERROR: Invalid region input")
    exit(1)

roi = frame[y:y+h, x:x+w]
if roi.size == 0:
    print("ERROR: Region out of bounds")
    exit(1)

# ============================================================
# DRAW ROI FOR CONFIRMATION
# ============================================================
annotated = frame.copy()
cv2.rectangle(
    annotated,
    (x, y),
    (x + w, y + h),
    (0, 255, 0),
    2
)

cv2.imwrite(ROI_IMG, annotated)
print(f"\nSaved annotated image: {ROI_IMG}")
print("VERIFY the green box is correct.\n")

# ============================================================
# HSV COMPUTE
# ============================================================
hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
pixels = hsv_roi.reshape(-1, 3)

h_min = max(int(pixels[:,0].min()) - H_MARGIN, 0)
h_max = min(int(pixels[:,0].max()) + H_MARGIN, 179)

s_min = max(int(pixels[:,1].min()) - S_MARGIN, 0)
s_max = min(int(pixels[:,1].max()) + S_MARGIN, 255)

v_min = max(int(pixels[:,2].min()) - V_MARGIN, 0)
v_max = min(int(pixels[:,2].max()) + V_MARGIN, 255)

profile = {
    "lower": [h_min, s_min, v_min],
    "upper": [h_max, s_max, v_max]
}

# ============================================================
# SAVE HSV FILE
# ============================================================
with open(HSV_PATH, "w") as f:
    json.dump(profile, f, indent=2)

print("\nHSV PROFILE CREATED:")
print(json.dumps(profile, indent=2))
print(f"\nSaved to: {HSV_PATH}")
