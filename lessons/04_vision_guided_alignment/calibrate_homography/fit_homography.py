#!/usr/bin/env python3
"""
Lesson 04 — Fit HOMOGRAPHY from camera (u,v) → table (x,y)

Uses ONLY the last N samples from samples.csv

This script is INTENTIONALLY destructive:
- Running it will OVERWRITE the active homography
- This is expected behavior
"""

import csv
import numpy as np
import cv2
from pathlib import Path

# --------------------------------
# PATHS
# --------------------------------
CALIB_DIR = Path(__file__).parent
PROJECT_ROOT = CALIB_DIR.parents[2]

CSV_PATH = CALIB_DIR / "samples.csv"
OUT_PATH = (
    PROJECT_ROOT
    / "lessons/04_vision_guided_alignment/data/homography_matrix.npy"
)

USE_LAST_N = 8   # 7 or 8 is fine

# --------------------------------
# LOAD CSV
# --------------------------------
if not CSV_PATH.exists():
    raise FileNotFoundError(f"Samples file not found: {CSV_PATH}")

rows = []
with open(CSV_PATH, newline="") as f:
    reader = csv.reader(f)
    for r in reader:
        if len(r) >= 4:
            rows.append(r)

# Detect header
try:
    float(rows[0][0])
    start = 0
except ValueError:
    start = 1

data = rows[start:]

if len(data) < USE_LAST_N:
    raise RuntimeError(
        f"Not enough samples ({len(data)}) — need at least {USE_LAST_N}"
    )

data = data[-USE_LAST_N:]

# --------------------------------
# PREP DATA
# --------------------------------
uv = []
xy = []

for r in data:
    u, v, x, y = map(float, r[:4])
    uv.append([u, v])
    xy.append([x, y])

uv = np.array(uv, dtype=np.float32)
xy = np.array(xy, dtype=np.float32)

# --------------------------------
# FIT HOMOGRAPHY
# --------------------------------
H, _ = cv2.findHomography(uv, xy, method=0)
np.save(OUT_PATH, H)

print("\n=== HOMOGRAPHY FIT COMPLETE ===")
print(f"Using last {USE_LAST_N} samples")
print(f"Saved to: {OUT_PATH}")
print("\nH =\n", H)

# --------------------------------
# ERROR CHECK
# --------------------------------
errors = []

for i in range(len(uv)):
    uv_h = np.array([uv[i][0], uv[i][1], 1.0])
    xy_hat = H @ uv_h
    xy_hat /= xy_hat[2]

    dx = xy_hat[0] - xy[i][0]
    dy = xy_hat[1] - xy[i][1]
    err = np.sqrt(dx * dx + dy * dy)
    errors.append(err)

    print(f"  Sample {i+1:02d}: {err:6.2f} mm")

print(f"\nMean error: {np.mean(errors):.2f} mm")
print(f"Max  error: {np.max(errors):.2f} mm")
