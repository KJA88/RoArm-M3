#!/usr/bin/env python3
"""
Headless HSV Profile Creator

Workflow:
1. Capture a camera snapshot
2. User opens image manually
3. User provides a pixel region (x,y,w,h)
4. Script computes HSV range
5. Saves hsv/<name>.json
"""

import cv2
import json
import os
import numpy as np
from picamera2 import Picamera2

# ============================================================
# CONFIG
# ============================================================
SAVE_DIR = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv"
)

SNAP_PATH = "/tmp/hsv_snapshot.jpg"

H_MARGIN = 10
S_MARGIN = 40
V_MARGIN = 40

# ============================================================
# NAME
# ============================================================
name = input("Enter object/color name (e.g. tool_marker): ").strip()
if not name:
    print("ERROR: name cannot be empty")
    exit(1)

os.makedirs(SAVE_DIR, exist_ok=True)
save_path = os.path.join(SAVE_DIR, f"{name}.json")

# ============================================================
# SNAPSHOT
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

cv2.imwrite(SNAP_PATH, frame)
print(f"\nSnapshot saved to {SNAP_PATH}")
print("Open it in any image viewer and find the marker region.\n")

# ============================================================
# REGION INPUT
# ============================================================
print("Enter pixel region containing ONLY the marker.")
print("Format: x y width height")
print("Example: 600 340 80 80\n")

try:
    x, y, w, h = map(int, input("Region: ").split())
except Exception:
    print("ERROR: Invalid input")
    exit(1)

roi = frame[y:y+h, x:x+w]
if roi.size == 0:
    print("ERROR: Region out of bounds")
    exit(1)

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
# SAVE
# ============================================================
with open(save_path, "w") as f:
    json.dump(profile, f, indent=2)

print("\nHSV profile created:")
print(json.dumps(profile, indent=2))
print(f"\nSaved to: {save_path}")
