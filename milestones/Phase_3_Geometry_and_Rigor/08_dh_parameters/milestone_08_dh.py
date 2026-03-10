#!/usr/bin/env python3
"""
Milestone 08: Denavit–Hartenberg Parameters

GOAL:
Formally model the RoArm-M3 kinematic chain using DH parameters
and compute Forward Kinematics (FK) deterministically.

NO HARDWARE
NO SERIAL
PURE MATH
"""

import math
import numpy as np

# ---- DH TABLE (example structure; values to be refined later) ----
# Each row: [a, alpha, d, theta]
# Units: mm, radians

DH_TABLE = [
    # Base -> Shoulder
    {"a": 0,   "alpha": math.pi/2, "d": 120, "theta": 0.0},
    # Shoulder -> Elbow
    {"a": 238, "alpha": 0.0,        "d": 0,   "theta": 0.0},
    # Elbow -> Wrist
    {"a": 316, "alpha": 0.0,        "d": 0,   "theta": 0.0},
]

def dh_transform(a, alpha, d, theta):
    """Standard DH homogeneous transform"""
    return np.array([
        [math.cos(theta), -math.sin(theta)*math.cos(alpha),  math.sin(theta)*math.sin(alpha), a*math.cos(theta)],
        [math.sin(theta),  math.cos(theta)*math.cos(alpha), -math.cos(theta)*math.sin(alpha), a*math.sin(theta)],
        [0,               math.sin(alpha),                  math.cos(alpha),                 d],
        [0,               0,                                 0,                                1],
    ])

def forward_kinematics(joint_angles):
    """Compute FK given joint angles"""
    T = np.eye(4)
    for i, angle in enumerate(joint_angles):
        row = DH_TABLE[i]
        T = T @ dh_transform(row["a"], row["alpha"], row["d"], angle)
    return T

if __name__ == "__main__":
    # Test cases
    test_sets = [
        ("ALL_ZERO", [0.0, 0.0, 0.0]),
        ("ELBOW_BENT", [0.0, 0.5, 0.0]),
        ("SHOULDER_UP", [0.5, 0.0, 0.0]),
    ]

    print("\n--- Milestone 08: DH Forward Kinematics ---")
    for name, joints in test_sets:
        T = forward_kinematics(joints)
        pos = T[:3, 3]
        print(f"\nCase: {name}")
        print(f"Joint Angles (rad): {joints}")
        print(f"TCP Position (mm): X={pos[0]:.2f} Y={pos[1]:.2f} Z={pos[2]:.2f}")

    print("\n[OK] DH model produces repeatable FK output.")
