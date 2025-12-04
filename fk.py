#!/usr/bin/env python3
import numpy as np
import json

# Load DH parameters
with open("calibrated_dh.json", "r") as f:
    dh = json.load(f)

alpha = np.array(dh["alpha"], dtype=float)
a     = np.array(dh["a"],     dtype=float)
d     = np.array(dh["d"],     dtype=float)
theta_offset = np.array(dh["theta_offset"], dtype=float)

def dh_transform(theta, d_i, a_i, alpha_i):
    """Standard DH transform for one joint."""
    ct = np.cos(theta)
    st = np.sin(theta)
    ca = np.cos(alpha_i)
    sa = np.sin(alpha_i)

    return np.array([
        [ ct, -st * ca,  st * sa, a_i * ct],
        [ st,  ct * ca, -ct * sa, a_i * st],
        [  0,       sa,      ca,      d_i],
        [  0,        0,       0,        1]
    ])

def forward_kinematics(joints):
    """
    joints: [j1..j6] in radians (your raw sensor values)
    Returns:
      xyz : np.array([X, Y, Z]) in mm
      R   : 3x3 rotation matrix
    World frame:
      X+ = forward
      Y+ = right
      Z+ = up from TABLE
    """
    j = np.array(joints, dtype=float)
    th = j + theta_offset  # convert to DH theta

    T = np.eye(4)
    # Only iterate over the first 5 joints for the DH chain
    # The 6th joint (gripper) has 0 link length (a=0, d=0) and is for the tool frame.
    for i in range(6): 
        T = T @ dh_transform(th[i], d[i], a[i], alpha[i])

    xyz = T[:3, 3]
    R   = T[:3, :3]
    return xyz, R

if __name__ == "__main__":
    # Test pose: Arm straight up, elbow straight, base forward (shoulder sensor reads ~0)
    test_up = [0, 0, 0, 0, 0, 0] 
    xyz_up, _ = forward_kinematics(test_up)
    print("FK(0,0,0,0,0,0) ->", xyz_up)
