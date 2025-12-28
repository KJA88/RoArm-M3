#!/usr/bin/env python3
"""
Lesson 06 – Calibration Processor
Calculates the mapping from pixels to millimeters.
"""

import pandas as pd
import numpy as np
import os

# Paths
HOME = os.path.expanduser("~")
CSV_PATH = os.path.join(HOME, "RoArm/lessons/04_camera_robot_calib/cam_robot_samples.csv")
SAVE_PATH = os.path.join(HOME, "RoArm/lessons/06_transform_and_depth/calibration_matrix.npy")

def run_calibration():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    # 1. Load data
    df = pd.read_csv(CSV_PATH)
    
    # 2. Filter out the glitch (Z=-93) automatically
    df_clean = df[df['z'] > 0].copy()
    
    # 3. Solve for M: [u, v, 1] @ M = [x, y]
    src = df_clean[['u', 'v']].values
    src_padded = np.column_stack([src, np.ones(src.shape[0])])
    dst = df_clean[['x', 'y']].values

    # Least Squares math finds the "best fit" mapping
    M, _, _, _ = np.linalg.lstsq(src_padded, dst, rcond=None)

    # 4. Save the "Brain"
    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    np.save(SAVE_PATH, M)
    
    print("\n" + "="*30)
    print("LESSON 06 CALIBRATION COMPLETE")
    print("="*30)
    print(f"Matrix saved to: {SAVE_PATH}")
    print("The robot now has a 'predictive' map of the table.")
    print("="*30)

if __name__ == "__main__":
    run_calibration()