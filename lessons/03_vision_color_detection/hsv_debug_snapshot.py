#!/usr/bin/env python3
"""
HSV Debug Snapshot — SAFE VERSION (EXTENDED)

- Green / blue behavior unchanged
- Red supported via optional multi-range
- Always saves:
    - raw
    - mask
    - annotated
    - saturation colormap
    - value colormap
- All outputs go into ./debug/
"""

import json
import numpy as np
import cv2
from pathlib import Path
from picamera2 import Picamera2

# ===============================
# PATHS
# ===============================
SCRIPT_DIR = Path(__file__).resolve().parent
PROFILES_DIR = SCRIPT_DIR / "profiles"
DEBUG_DIR = SCRIPT_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

RAW_IMG  = DEBUG_DIR / "debug_raw.jpg"
MASK_IMG = DEBUG_DIR / "debug_mask.jpg"
ANN_IMG  = DEBUG_DIR / "debug_annotated.jpg"
S_IMG    = DEBUG_DIR / "debug_s_colormap.jpg"
V_IMG    = DEBUG_DIR / "debug_v_colormap.jpg"

# ===============================
# LIST PROFILES
# ===============================
profiles = sorted(PROFILES_DIR.glob("*.json"))
if not profiles:
    raise RuntimeError("No HSV profiles found")

print("\nAvailable HSV profiles:")
for i, p in enumerate(profiles):
    print(f"  [{i}] {p.name}")

idx = int(input("\nSelect HSV profile index: ").strip())
HSV_PATH = profiles[idx]

print(f"\nUsing HSV profile: {HSV_PATH.name}")

with open(HSV_PATH) as f:
    cfg = json.load(f)

MIN_AREA = cfg.get("min_area", 300)

# ===============================
# CAMERA
# ===============================
picam2 = Picamera2()
cam_cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cam_cfg)
picam2.start()

frame = picam2.capture_array()
picam2.close()

cv2.imwrite(str(RAW_IMG), frame)

# ===============================
# HSV + MASK
# ===============================
hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
h, s, v = cv2.split(hsv)

if "ranges" in cfg:
    # RED (multi-range)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for r in cfg["ranges"]:
        lo = np.array(r["lower"], np.uint8)
        hi = np.array(r["upper"], np.uint8)
        mask |= cv2.inRange(hsv, lo, hi)
else:
    # GREEN / BLUE
    lo = np.array(cfg["lower"], np.uint8)
    hi = np.array(cfg["upper"], np.uint8)
    mask = cv2.inRange(hsv, lo, hi)

cv2.imwrite(str(MASK_IMG), mask)

# ===============================
# COLORMAPS (DIAGNOSTIC ONLY)
# ===============================
s_color = cv2.applyColorMap(s, cv2.COLORMAP_JET)
v_color = cv2.applyColorMap(v, cv2.COLORMAP_JET)

cv2.imwrite(str(S_IMG), s_color)
cv2.imwrite(str(V_IMG), v_color)

# ===============================
# DETECTION
# ===============================
annotated = frame.copy()
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

if contours:
    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area >= MIN_AREA:
        M = cv2.moments(c)
        if M["m00"] != 0:
            u = int(M["m10"] / M["m00"])
            v_ = int(M["m01"] / M["m00"])
            cv2.drawContours(annotated, [c], -1, (0, 255, 0), 2)
            cv2.circle(annotated, (u, v_), 6, (0, 255, 0), -1)

cv2.imwrite(str(ANN_IMG), annotated)

# ===============================
# DONE
# ===============================
print("\nSaved to ./debug/:")
print(" ", RAW_IMG.name)
print(" ", MASK_IMG.name)
print(" ", ANN_IMG.name)
print(" ", S_IMG.name)
print(" ", V_IMG.name)
print("\nDONE.")
