#!/usr/bin/env python3
import sys
import os
import subprocess
import numpy as np
import time
from math import sqrt
from ik import inverse_kinematics

# --- Configuration (Must match your system settings) ---
ROARM = "./roarm_control.py"

G_OPEN   = 0.5
G_CLOSED = 3.0
# OPTIMIZATION: Reduce angular step size to force more micro-steps (smoothness)
STEP_SIZE_RAD = 0.01    # Max joint motion per step (smoothness)
# OPTIMIZATION: Increase stream rate for fluid movement
STREAM_HZ = 50          # Update frequency (50 times per second)
STREAM_DELAY = 1 / STREAM_HZ

# --- Global State Mimicry (for IK warm starts) ---
LAST_JOINTS_5DOF = np.array([0.0, 0.5, 0.5, 0.0, 0.0], dtype=float) 

# --- Waypoints ---
MISSION_SEQUENCE = [
    {"x": 200, "y": 0,   "z": 200, "r": 0.0, "g": G_OPEN},   # Home Start
    {"x": 250, "y": 0,   "z": 150, "r": 0.0, "g": G_OPEN},   # Approach A
    {"x": 250, "y": 0,   "z": 100, "r": 0.0, "g": G_OPEN},   # Pick A
    {"x": 250, "y": 0,   "z": 100, "r": 0.0, "g": G_CLOSED}, # Grip
    {"x": 250, "y": 0,   "z": 180, "r": 0.0, "g": G_CLOSED}, # Lift
    {"x": 100, "y": 150, "z": 180, "r": 0.0, "g": G_CLOSED}, # Approach B
    {"x": 100, "y": 150, "z": 100, "r": 0.0, "g": G_CLOSED}, # Drop B
    {"x": 100, "y": 150, "z": 100, "r": 0.0, "g": G_OPEN},   # Release
    {"x": 100, "y": 150, "z": 180, "r": 0.0, "g": G_OPEN},   # Retreat
    {"x": 200, "y": 0,   "z": 200, "r": 0.0, "g": G_OPEN},   # Return home
]

# --- Joint Interpolation Engine ---
def interpolate_joints(j1, j2, step_size=STEP_SIZE_RAD):
    """
    Generates micro-steps between two joint vectors based on max angular distance.
    """
    diff = np.abs(j2 - j1)
    # Calculate steps based on the joint that moves the most
    steps = int(np.max(diff) / step_size) + 1 

    out = []
    for i in range(1, steps + 1):
        t = i / steps
        out.append(j1 + t * (j2 - j1))
    return out

def calculate_ik_and_stream(j1, p2):
    """
    Calculates IK for the target waypoint and streams interpolated steps live.
    """
    global LAST_JOINTS_5DOF

    target_xyz = np.array([p2["x"], p2["y"], p2["z"]], dtype=float)
    # NOTE: The IK solver must be available and functional via 'ik.py'
    sol = inverse_kinematics(target_xyz, p2["r"], LAST_JOINTS_5DOF)
    
    if sol is None:
        print(f"[IK FAILED] Cannot move to ({p2['x']}, {p2['y']}, {p2['z']}). Skipping.")
        return j1 

    LAST_JOINTS_5DOF = sol[:5]
    j2 = np.array([sol[0], sol[1], sol[2], sol[3], sol[4], p2["g"]])

    # Generate microsteps between the current joint position (j1) and the target (j2)
    microsteps = interpolate_joints(j1, j2)
    
    # Track the number of commands sent for diagnostics
    print(f"-> Streaming {len(microsteps)} micro-steps...")

    for j_step in microsteps:
        # T=102 is non-blocking (via 'direct_move'). We pass all 6 joint angles.
        cmd = [sys.executable, ROARM, "direct_move"] + [str(v) for v in j_step]
        
        # Execute the non-blocking command
        subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=1) 
        time.sleep(STREAM_DELAY) # Maintain consistent stream rate

    return j2 # Return the final joint vector

# --- Main Streaming Loop ---
def main():
    print(f"\n--- Starting T=102 Live Streaming Engine ({STREAM_HZ} Hz) ---")
    
    # 0. Initial Setup
    try:
        # Torque ON using the safe, pre-existing torque_on action
        subprocess.run([sys.executable, ROARM, "torque_on"], check=True, timeout=5)
        
        # 1. Calculate and move to the initial start point (Home)
        # Use a zero array as the starting point for the first IK calculation
        j_start = calculate_ik_and_stream(np.array([0.0]*6), MISSION_SEQUENCE[0])
        last_joints = j_start
        print("\nReady to stream motion.")
        
        # 2. Execute the entire mission sequence
        for i, point in enumerate(MISSION_SEQUENCE[1:]):
            print(f"Streaming step {i+2}/{len(MISSION_SEQUENCE)}: {point}")
            
            # Stream from the last successful joint position to the new target
            last_joints = calculate_ik_and_stream(last_joints, point)

    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Mission aborted: {e}")
    finally:
        print("\nStreaming finished.")


if __name__ == "__main__":
    main()
