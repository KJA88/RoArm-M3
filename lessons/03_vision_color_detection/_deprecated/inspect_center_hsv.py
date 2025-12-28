#!/usr/bin/env python3
"""
inspect_center_hsv.py (better HSV capture)

Problem we fix:
- If the center patch is gray/dark (low saturation), Hue becomes meaningless and spans 0..179.
- That makes the mask cover the whole image.

Fix:
- Only compute Hue stats on "good color" pixels: S>=60 and V>=60.
- Also force S/V lower bounds to avoid gray background.

Writes:
  lessons/03_vision_color_detection/hsv_config.json
  lessons/03_vision_color_detection/frame_with_patch.jpg
"""

import json
from pathlib import Path
import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FRAME_PATH = SCRIPT_DIR / "frame.jpg"
OUT_WITH_PATCH = SCRIPT_DIR / "frame_with_patch.jpg"
OUT_JSON = SCRIPT_DIR / "hsv_config.json"

PATCH_HALF = 12

# "Good color" thresholds:
S_GOOD = 60
V_GOOD = 60

# How tight the Hue window should be around the mean:
H_WINDOW = 12  # +/- 12 degrees

def clamp(v, lo, hi):
    return int(max(lo, min(hi, v)))

def main():
    if not FRAME_PATH.exists():
        print(f"ERROR: missing {FRAME_PATH}")
        print("Run: python3 lessons/03_vision_color_detection/camera_snap.py")
        return

    img = cv2.imread(str(FRAME_PATH))
    if img is None:
        print(f"ERROR: could not load image {FRAME_PATH}")
        return

    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2

    x1 = max(0, cx - PATCH_HALF)
    y1 = max(0, cy - PATCH_HALF)
    x2 = min(w, cx + PATCH_HALF)
    y2 = min(h, cy + PATCH_HALF)

    # Visual confirm image
    vis = img.copy()
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.drawMarker(vis, (cx, cy), (255, 0, 0),
                   markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
    cv2.imwrite(str(OUT_WITH_PATCH), vis)

    patch = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)

    H = hsv[:, :, 0].astype(np.int32)
    S = hsv[:, :, 1].astype(np.int32)
    V = hsv[:, :, 2].astype(np.int32)

    good = (S >= S_GOOD) & (V >= V_GOOD)
    good_count = int(good.sum())
    total = H.size
    print(f"Patch good-color pixels: {good_count}/{total} ({100.0*good_count/total:.1f}%)")

    if good_count < 20:
        print("ERROR: center patch is mostly gray/dark (low saturation).")
        print("Put the OBJECT you want to track dead-center and re-run camera_snap + this script.")
        return

    Hg = H[good]
    Sg = S[good]
    Vg = V[good]

    h_mean = float(Hg.mean())
    s_min, s_max = int(Sg.min()), int(Sg.max())
    v_min, v_max = int(Vg.min()), int(Vg.max())

    # Tight Hue bounds around mean
    h_lo = int(round(h_mean - H_WINDOW))
    h_hi = int(round(h_mean + H_WINDOW))

    # Handle wrap edges for "red-ish" near 0 or 179 by clamping
    h_lo = clamp(h_lo, 0, 179)
    h_hi = clamp(h_hi, 0, 179)

    # Force S/V lower bounds to avoid gray/background
    lower = [h_lo, max(80, s_min - 10), max(60, v_min - 10)]
    upper = [h_hi, min(255, s_max + 10), min(255, v_max + 10)]

    OUT_JSON.write_text(json.dumps({"lower": lower, "upper": upper}, indent=2))
    print("Wrote:", OUT_JSON)
    print("Patch image:", OUT_WITH_PATCH)
    print("lower:", lower)
    print("upper:", upper)

if __name__ == "__main__":
    main()
