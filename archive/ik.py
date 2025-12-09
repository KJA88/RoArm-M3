import numpy as np
from math import sin, cos, atan2, sqrt, pi

# --- Physical Parameters (Standard RoArm-M3-S) ---
L1 = 120.0  # Base to Shoulder (Vertical)
L2 = 130.0  # Shoulder to Elbow
L3 = 130.0  # Elbow to Wrist
L4 = 100.0  # Wrist to Gripper tip (Approx)

# --- INVERSE KINEMATICS FIX: Scaling Factor ---
# Divide X and Y by 3.8 to compensate for the 3.8x overshoot 
# (e.g., 460mm reached for 120mm command).
SCALE_FACTOR = 3.8

# --- Inverse Kinematics Solver ---
def inverse_kinematics(xyz, roll, last_joints_5dof):
    """
    Calculates joint angles [base, shoulder, elbow, wrist, roll] 
    for a given XYZ position and wrist roll.
    """
    x, y, z = xyz[0], xyz[1], xyz[2]
    
    # --- APPLY SCALING FIX ---
    x = x / SCALE_FACTOR
    y = y / SCALE_FACTOR
    
    # 1. Base Joint (J1)
    if x == 0 and y == 0:
        base = last_joints_5dof[0]
    else:
        base = atan2(y, x)

    # Calculate horizontal distance from base pivot
    D = sqrt(x**2 + y**2)
    
    # Effective vertical height (subtract L1)
    h = z - L1

    # Distance from shoulder pivot to wrist pivot
    R = sqrt(D**2 + h**2)

    # Check reach limits
    if R > (L2 + L3) or R < abs(L2 - L3):
        return None  # Cannot reach

    # 2. Elbow Joint (J3)
    # Using the Law of Cosines to find the angle at the elbow
    cos_elbow = (R**2 - L2**2 - L3**2) / (2 * L2 * L3)
    # Clamp cos_elbow to [-1, 1] to prevent math domain errors
    cos_elbow = max(-1, min(1, cos_elbow)) 
    
    elbow_angle_from_straight = atan2(sqrt(1 - cos_elbow**2), cos_elbow)
    elbow = pi - elbow_angle_from_straight  # J3 is typically measured from the straight-out position

    # 3. Shoulder Joint (J2)
    # Calculate the two angles that form J2
    alpha = atan2(h, D)
    beta = atan2(L3 * sin(elbow_angle_from_straight), L2 + L3 * cos(elbow_angle_from_straight))
    
    shoulder = alpha + beta # J2 is shoulder angle

    # 4. Wrist Joint (J4)
    # J4 is the angle required to point the gripper (relative to horizontal)
    wrist = roll - (shoulder + elbow) # Wrist angle compensates for shoulder and elbow

    # 5. Roll Joint (J5) - Not used in standard 5DOF model, but kept for completeness
    roll_joint = 0.0 

    # Return as a 6-element array: [base, shoulder, elbow, wrist, roll_joint, gripper]
    return np.array([base, shoulder, elbow, wrist, roll_joint, 0.0])
