#!/usr/bin/env python3
"""
Interactive HSV Profile Creator

- Asks for object/color name
- Opens camera view
- Click multiple points on the object
- Computes HSV min/max with margin
- Saves to:
  ~/RoArm/lessons/03_vision_color_detection/hsv/<name>.json
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

H_MARGIN = 10    # Hue tolerance
S_MARGIN = 40    # Saturation tolerance
V_MARGIN = 40    # Value tolerance

# ============================================================
# ASK FOR NAME
# ============================================================
name = input("Enter object/color name (e.g. tool_marker, red_block): ").strip()

if not name:
    print("ERROR: name cannot be empty")
    exit(1)

os.makedirs(SAVE_DIR, exist_ok=True)

save_path = os.path.join(SAVE_DIR, f"{name}.json")

print(f"\nHSV profile will be saved to:\n{save_path}\n")

# ============================================================
# CAMERA SETUP
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

hsv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# ============================================================
# CLICK HANDLER
# ============================================================
samples = []

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        hsv = param[y, x]
        samples.append(hsv)
        print(f"Clicked at ({x},{y}) -> HSV = {hsv}")

# ============================================================
# UI LOOP
# ============================================================
cv2.namedWindow("HSV Picker")
cv2.setMouseCallback("HSV Picker", on_mouse, hsv_img)

print("Click on the object multiple times.")
print("Press ENTER when done, ESC to cancel.\n")

while True:
    cv2.imshow("HSV Picker", frame)
    key = cv2.waitKey(20) & 0xFF

    if key == 13:  # ENTER
        break
    elif key == 27:  # ESC
        print("Cancelled.")
        cv2.destroyAllWindows()
        exit(0)

cv2.destroyAllWindows()

# ============================================================
# COMPUTE RANGE
# ============================================================
if len(samples) < 3:
    print("ERROR: Need at least 3 clicks.")
    exit(1)

samples = np.array(samples)

h_min = max(int(samples[:, 0].min()) - H_MARGIN, 0)
h_max = min(int(samples[:, 0].max()) + H_MARGIN, 179)

s_min = max(int(samples[:, 1].min()) - S_MARGIN, 0)
s_max = min(int(samples[:, 1].max()) + S_MARGIN, 255)

v_min = max(int(samples[:, 2].min()) - V_MARGIN, 0)
v_max = min(int(samples[:, 2].max()) + V_MARGIN, 255)

hsv_profile = {
    "lower": [h_min, s_min, v_min],
    "upper": [h_max, s_max, v_max]
}

# ============================================================
# SAVE FILE
# ============================================================
with open(save_path, "w") as f:
    json.dump(hsv_profile, f, indent=2)

print("\nSaved HSV profile:")
print(json.dumps(hsv_profile, indent=2))
print(f"\nFile written to: {save_path}")
