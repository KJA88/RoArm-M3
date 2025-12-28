#!/usr/bin/env python3
"""
Lesson 07 — Vision → Table XY Preview (NO MOTION)

- Uses HSV from Lesson 07
- Detects marker
- Converts (u,v) → (x,y)
- PRINTS target only
"""

import json
import os
import time
import numpy as np
import cv2
from picamera2 import Picamera2
from uv_to_xy_map import uv_to_xy

# ============================================================
# PATHS
# ============================================================
BASE_DIR = os.path.expanduser("~/RoArm/lessons/07_xy_table_mapping")
HSV_PATH = os.path.join(BASE_DIR, "hsv", "red.json")  # <-- your calibrated color

# ============================================================
# LOAD HSV
# ============================================================
with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

print("Loaded HSV:")
print("  MIN:", HSV_MIN)
print("  MAX:", HSV_MAX)

# ============================================================
# CAMERA
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

print("\n=== VISION → XY PREVIEW ===")
print("Place object on table")
print("Ctrl+C to exit\n")

# ============================================================
# LOOP
# ============================================================
try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 300:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    u = int(M["m10"] / M["m00"])
                    v = int(M["m01"] / M["m00"])

                    x, y = uv_to_xy(u, v)

                    print(
                        f"Detected u={u:4d}, v={v:4d} "
                        f"→ target x={x:7.1f}, y={y:7.1f}"
                    )

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nExiting preview")

finally:
    picam2.close()
