#!/usr/bin/env python3
"""
Lesson 07 — Homography-based UV → XY mapper

Loads homography_matrix_clean.npy
Used by future controllers (Lesson 08+)
"""

import numpy as np
import os

H_PATH = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping/homography_matrix_clean.npy"
)

if not os.path.exists(H_PATH):
    raise FileNotFoundError(
        "homography_matrix_clean.npy not found"
    )

H = np.load(H_PATH)

def uv_to_xy(u, v):
    uv_h = np.array([u, v, 1.0], dtype=float)
    xy_h = H @ uv_h
    xy_h /= xy_h[2]
    return float(xy_h[0]), float(xy_h[1])


if __name__ == "__main__":
    # quick sanity test
    test_uv = (640, 360)
    x, y = uv_to_xy(*test_uv)
    print(f"Test uv={test_uv} -> x={x:.2f}, y={y:.2f}")
