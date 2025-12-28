#!/usr/bin/env python3
"""
Lesson 07 — Fit HOMOGRAPHY from camera (u,v) → table (x,y)

Uses ONLY the last N samples from cam_table_samples.csv
"""

import csv
import numpy as np
import cv2
import os

CSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping/cam_table_samples.csv"
)

USE_LAST_N = 8   # ← CHANGE THIS if needed (7 or 8 is fine)

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(CSV_PATH)

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
    raise RuntimeError("Not enough rows to select last N samples")

data = data[-USE_LAST_N:]

uv = []
xy = []

for r in data:
    u, v, x, y = map(float, r[:4])
    uv.append([u, v])
    xy.append([x, y])

uv = np.array(uv, dtype=np.float32)
xy = np.array(xy, dtype=np.float32)

H, _ = cv2.findHomography(uv, xy, method=0)
np.save("homography_matrix.npy", H)

print("\n=== HOMOGRAPHY (LAST SAMPLES ONLY) ===")
print("Using last", USE_LAST_N, "samples")
print("H =\n", H)

errors = []
for i in range(len(uv)):
    uv_h = np.array([uv[i][0], uv[i][1], 1.0])
    xy_hat = H @ uv_h
    xy_hat /= xy_hat[2]
    dx = xy_hat[0] - xy[i][0]
    dy = xy_hat[1] - xy[i][1]
    err = np.sqrt(dx*dx + dy*dy)
    errors.append(err)
    print(f"  Sample {i+1:02d}: {err:6.2f} mm")

print(f"\nMean error: {np.mean(errors):.2f} mm")
print(f"Max  error: {np.max(errors):.2f} mm")
