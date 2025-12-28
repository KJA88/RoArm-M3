#!/usr/bin/env python3
"""
Lesson 07 — Fit Camera (u,v) → Table (x,y) Affine Mapping
(HEADERLESS CSV VERSION)
"""

import numpy as np
import csv
from pathlib import Path

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path.home() / "RoArm/lessons/07_xy_table_mapping"
CSV_PATH = BASE_DIR / "cam_table_samples_clean.csv"

# ============================================================
# LOAD DATA (HEADERLESS)
# ============================================================
uv = []
xy = []

with open(CSV_PATH) as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 4:
            continue
        u = float(row[0])
        v = float(row[1])
        x = float(row[2])
        y = float(row[3])
        uv.append([u, v])
        xy.append([x, y])

uv = np.array(uv)
xy = np.array(xy)

assert len(uv) >= 4, "Need at least 4 samples for affine fit"

# ============================================================
# FIT AFFINE TRANSFORM
# ============================================================
# Add bias term to UV
ones = np.ones((uv.shape[0], 1))
UV1 = np.hstack([uv, ones])   # [u v 1]

# Solve least squares: UV1 @ A.T = XY
A, residuals, rank, s = np.linalg.lstsq(UV1, xy, rcond=None)
A = A.T   # shape: 2 x 3

# ============================================================
# RESULTS
# ============================================================
print("\n=== AFFINE CAMERA → TABLE MAP ===")
print("x = a*u + b*v + c")
print("y = d*u + e*v + f\n")

print(f"a = {A[0,0]: .6f}")
print(f"b = {A[0,1]: .6f}")
print(f"c = {A[0,2]: .6f}")
print()
print(f"d = {A[1,0]: .6f}")
print(f"e = {A[1,1]: .6f}")
print(f"f = {A[1,2]: .6f}")

# ============================================================
# ERROR CHECK
# ============================================================
pred = UV1 @ A.T
err = np.linalg.norm(pred - xy, axis=1)

print("\nPer-sample error (mm):")
for i, e in enumerate(err):
    print(f"  Sample {i+1:02d}: {e:.2f} mm")

print(f"\nMean error: {err.mean():.2f} mm")
print(f"Max  error: {err.max():.2f} mm")
