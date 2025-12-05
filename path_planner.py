#!/usr/bin/env python3
import numpy as np
import time
import sys
import serial
import json

# --- Core Imports ---
from fk import forward_kinematics
from ik import inverse_kinematics

# --- Configuration & Global State ---
PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
LAST_JOINTS_5DOF = np.array([0.0, 0.5, 0.5, 0.0, 0.0], dtype=float) 

# --- Sender Function ---

def send_command(x, y, z, r, g, command_type):
    """
    Sends XYZ coordinates and Roll/Gripper commands using non-blocking T:1041.
    """
    cmd = {
        "T": command_type,
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "t": 0.0, # Fixed Pitch angle (T axis) for streaming stability
        "r": float(r),
        "g": float(g),
    }
    
    try:
        with serial.Serial(PORT, 115200, timeout=1) as s:
            s.write((json.dumps(cmd) + "\n").encode("utf-8"))
            s.flush()
    except serial.SerialException as e:
        print(f"ERROR: Could not send command via serial: {e}")

# --- Trajectory Planning Functions ---

def move_single_point_init(target_xyz, target_roll=0.0, target_gripper=0.0):
    """
    Moves the arm to the initial point using the stable T:104 command (blocking)
    and initializes the warm start.
    """
    global LAST_JOINTS_5DOF
    
    print(f"Initializing position to: {target_xyz}")
    
    initial_guess = LAST_JOINTS_5DOF
    joints_5dof = inverse_kinematics(target_xyz, target_roll, initial_guess) 
    
    if joints_5dof is None:
        print("Warning: IK failed to find initial position.")
        return False
    
    LAST_JOINTS_5DOF = joints_5dof[0:5] 
    
    # Use T:104 (blocking XYZ) for the smooth initial move
    cmd = {
        "T": 104,
        "x": float(target_xyz[0]),
        "y": float(target_xyz[1]),
        "z": float(target_xyz[2]),
        "t": 0.0,
        "r": float(target_roll),
        "g": float(target_gripper),
        "spd": 25, # Speed parameter for T:104
    }
    
    try:
        with serial.Serial(PORT, 115200, timeout=1) as s:
            s.write((json.dumps(cmd) + "\n").encode("utf-8"))
            s.flush()
    except serial.SerialException as e:
        print(f"ERROR: Could not send command via serial: {e}")
        return False
        
    time.sleep(1.5) # Wait for the arm to settle
    return True

def linear_move(start_xyz, end_xyz, steps, target_roll=0.0, target_gripper=0.0):
    """
    Calculates a linear path and moves the arm point-by-point using T:1041.
    """
    global LAST_JOINTS_5DOF
    
    if steps < 2:
        print("Error: Linear move requires at least 2 steps (start and end).")
        return

    print(f"\n--- Starting Streaming Move: {steps} steps (T:1041) ---")
    print(f"Start: {start_xyz}, End: {end_xyz}")

    path_vector = end_xyz - start_xyz
    step_vector = path_vector / (steps - 1)
    
    for i in range(steps):
        target_xyz = start_xyz + (step_vector * i)
        
        # 1. Warm-Start IK is still run to prevent joint flips
        initial_guess = LAST_JOINTS_5DOF
        joints_5dof = inverse_kinematics(target_xyz, target_roll, initial_guess) 
        
        if joints_5dof is None:
            print(f"Warning: IK failed at step {i} / {steps}. Skipping step.")
            continue
        
        LAST_JOINTS_5DOF = joints_5dof[0:5] # Update Warm Start
        
        # 2. SEND COORDINATES DIRECTLY using non-blocking T:1041
        send_command(target_xyz[0], target_xyz[1], target_xyz[2], 
                     target_roll, target_gripper, 1041)
        
        # 3. Minimal delay for serial buffer
        time.sleep(0.015) 

    print("--- Streaming Move Complete ---")

def main():
    start = np.array([150.0, 0.0, 100.0])
    end = np.array([350.0, 0.0, 180.0])
    # REDUCED STEPS to 50 for 3x FASTER, more continuous motion
    num_steps = 50 
    
    if not move_single_point_init(start):
        return
    
    # Run the upward motion
    print("\n--- Testing UPWARD Streaming Motion (FASTER) ---")
    linear_move(start, end, steps=num_steps)

    time.sleep(1.5)
    
    # Test Downward Trajectory 
    print("\n--- Testing DOWNWARD Streaming Motion (FASTER) ---")
    linear_move(end, start, steps=num_steps) 

if __name__ == "__main__":
    main()
