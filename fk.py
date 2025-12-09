#!/usr/bin/env python3
import numpy as np

# --- LINK LENGTHS (mm) ---
H_BASE = 127.0      # table -> J1 pivot height
L1 = 236.0          # J1 -> J2 vertical
L2 = 145.0          # J2 -> J3 vertical
L3 = 55.0           # J3 -> J4 vertical
L4 = 120.0          # J4 -> end-effector vertical

OFF_23 = 30.0       # fixed J2 → J3 horizontal offset (base X direction)
OFF_45 = 13.3       # rotating offset from J4 to J5 (local X direction)

def rot_z(theta):
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([
        [c,-s,0,0],
        [s, c,0,0],
        [0, 0,1,0],
        [0, 0,0,1]
    ])

def rot_y(theta):
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([
        [ c,0,s,0],
        [ 0,1,0,0],
        [-s,0,c,0],
        [ 0,0,0,1]
    ])

def trans(x,y,z):
    return np.array([
        [1,0,0,x],
        [0,1,0,y],
        [0,0,1,z],
        [0,0,0,1]
    ])

def forward_kinematics(j):
    j1, j2, j3, j4, j5, _ = j

    # 1. Start at base frame
    T = np.eye(4)

    # 2. Move up to J1 pivot (fixed)
    T = T @ trans(0,0,H_BASE)

    # 3. Base rotation J1
    T = T @ rot_z(j1)

    # 4. Move up to J2
    T = T @ trans(0,0,L1)

    # 5. Shoulder pitch J2
    T = T @ rot_y(j2)

    # (Fixed) J2 → J3 horizontal offset
    T = T @ trans(OFF_23,0,0)

    # 6. Move up to J3
    T = T @ trans(0,0,L2)

    # 7. Elbow pitch J3
    T = T @ rot_y(j3)

    # 8. Move up to J4
    T = T @ trans(0,0,L3)

    # 9. Wrist pitch J4
    T = T @ rot_y(j4)

    # (Rotating) J4 → J5 offset (local X)
    T = T @ trans(OFF_45,0,0)

    # 10. Move through J5 segment
    T = T @ trans(0,0,L4)

    # 11. Wrist roll J5
    T = T @ rot_z(j5)

    xyz = T[:3,3]
    return xyz, T[:3,:3]

if __name__ == "__main__":
    # Test FK
    J = np.array([0,0,np.pi/2,0,0,0])
    xyz,_ = forward_kinematics(J)
    print("FK:", xyz)
