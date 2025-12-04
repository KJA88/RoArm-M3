#!/usr/bin/env python3
import numpy as np
from scipy.optimize import least_squares
from fk import forward_kinematics

# We now solve IK for joints [J1..J5]; J6 fixed to 0
JOINTS_USED = 5

# Joint limits (rad) – conservative for safety
limits_min = np.array([
    -3.0,   # J1 base (yaw)
    -1.8,   # J2 shoulder (pitch)
    -0.40,  # J3 elbow (pitch)
    -2.0,   # J4 wrist pitch
    -3.0    # J5 wrist roll
])
limits_max = np.array([
     3.0,   # J1 base (yaw)
     1.8,   # J2 shoulder (pitch)
     2.15,  # J3 elbow (pitch)
     2.0,   # J4 wrist pitch
     3.0    # J5 wrist roll
])

# Weight for the Roll error vs. position error
ROLL_WEIGHT = 50.0 

def ik_objective(joints, target_xyz_roll):
    """
    Optimization objective: minimize the residual for XYZ position AND Roll angle.
    joints: [J1..J5] being optimized
    target_xyz_roll: [X, Y, Z, Target Roll]
    """
    target_xyz = target_xyz_roll[:3]
    target_roll = target_xyz_roll[3]
    
    # Append fixed J6=0 to run FK
    full_joints = np.array(
        [joints[0], joints[1], joints[2], joints[3], joints[4], 0.0],
        dtype=float
    )
    
    xyz, R = forward_kinematics(full_joints)
    
    # Residual for Position (X, Y, Z)
    pos_residual = xyz - target_xyz
    
    # Residual for Roll: We want the solver to set J5 to match the target roll.
    # The solver will use J5's current angle to meet the target_roll angle.
    roll_residual = (joints[4] - target_roll) * ROLL_WEIGHT
    
    # Return the combined residual vector (3 positional + 1 scaled roll)
    return np.concatenate([pos_residual, [roll_residual]])

def inverse_kinematics(target_xyz, target_roll, initial_guess=None):
    """
    Solve IK for XYZ position and Roll orientation.
    Returns [J1..J6] joint array (rad) or None if solver fails.
    """
    if initial_guess is None:
        # Initial guess for [J1, J2, J3, J4, J5] (size 5)
        initial_guess = np.array([0.0, 0.5, 0.5, 0.0, 0.0], dtype=float)
        
    # Combine target XYZ and Roll into a single array for the objective function
    target_xyz_roll = np.array([*target_xyz, target_roll], dtype=float)

    result = least_squares(
        ik_objective,
        initial_guess,
        args=(target_xyz_roll,),
        method="trf",
        max_nfev=300
    )

    if not result.success:
        print("IK SOLVER FAILED:", result.message)
        return None

    j = result.x

    # Clamp the solution to physical limits
    j_clamped = np.clip(j, limits_min, limits_max)
    
    # Build full joint vector [J1..J6]
    full = np.array([j_clamped[0],
                     j_clamped[1],
                     j_clamped[2],
                     j_clamped[3],
                     j_clamped[4], # J5 Roll is now calculated
                     0.0])         # J6 gripper ignored
                     
    return full

if __name__ == "__main__":
    # Test target: 250 mm forward, 0 roll
    target_xyz = np.array([250.0, 0.0, 150.0])
    target_roll = 0.0
    sol = inverse_kinematics(target_xyz, target_roll)
    
    if sol is not None:
        print("IK solution:", sol)
        xyz, _ = forward_kinematics(sol)
        print("FK check (should match target) ->", xyz)
