#
# --- HOW THE PATH PLANNING SCRIPT WORKS ---
#
# The coordinates Start: [150, 0, 100] and End: [350, 0, 180] are not sent 
# to the robot directly in one command. They are used by the Python code 
# to generate the trajectory:
#
# 1. Linear Interpolation (Math)
# The path_planner.py script uses linear interpolation (L.I.) to calculate 
# all the points that lie on the straight line between the start and end coordinates.
# The total path distance is divided into 50 segments (since we set num_steps = 50).
# The script calculates the exact X,Y,Z coordinate for each of the 50 intermediate points.
#
# 2. Streaming Command (T:1041)
# The script then enters a fast loop:
# Loop 1: Calculate Point 1's XYZ and send it via T:1041.
# Loop 2: Calculate Point 2's XYZ and send it via T:1041.
# ...
# Loop 50: Calculate Point 50's XYZ and send it via T:1041.
# Because the T:1041 command is non-blocking and the points are sent so quickly, 
# the robot executes the movement as one continuous, smooth straight line, even 
# though it's receiving 50 separate commands.
#
# 3. The End Goal
# The End Point ([350, 0, 180]) is simply the last coordinate sent by the loop.
# This entire process is why you only need to define the start and end points 
# in the code—the script handles the thousands of calculations and serial commands 
# required for the smooth motion.
#
# --------------------------------------------------------------------------
#

#!/usr/bin/env python3
import numpy as np
import time
import sys
import serial
import json

# --- Core Imports ---
# FK/IK are still needed for the initial pose and for the Warm-Start guess
from fk import forward_kinematics
from ik import inverse_kinematics

# --- Configuration & Global State ---
PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
LAST_JOINTS_5DOF = np.array([0.0, 0.5, 0.5, 0.0, 0.0], dtype=float) 

# --- Sender Function ---

def send_command(x, y, z, r, g, command_type):
    """
    Sends XYZ coordinates and Roll/Gripper commands.
    Uses T:1041 (CMD_XYZT_DIRECT_CTRL) for non-blocking streaming.
    T:1041 does not use speed or acceleration parameters.
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
    
    # Use T:104 (blocking XYZ) for initialization move, which supports speed
    if command_type == 104:
        cmd["spd"] = 25
        
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
    
    # We use IK here only to get a good warm start guess
    initial_guess = LAST_JOINTS_5DOF
    joints_5dof = inverse_kinematics(target_xyz, target_roll, initial_guess) 
    
    if joints_5dof is None:
        print("Warning: IK failed to find initial position.")
        return False
    
    LAST_JOINTS_5DOF = joints_5dof[0:5] 
    
    # Use T:104 (blocking XYZ with interpolation) for the smooth initial move
    send_command(target_xyz[0], target_xyz[1], target_xyz[2], 
                 target_roll, target_gripper, 104)
        
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
    # --- PATH DEFINITION: Defines the start and end coordinates for the trajectory ---
    
    # START POINT: Close, low, and centered.
    # [150mm Forward, 0mm Side, 100mm Up]
    start = np.array([150.0, 0.0, 100.0])
    
    # END POINT: Farther, higher, and centered.
    # [350mm Forward, 0mm Side, 180mm Up]
    end = np.array([350.0, 0.0, 180.0])
    
    # STREAMING PARAMETER: Number of steps used for linear interpolation.
    # We use 50 steps for fast, continuous motion that overcomes serial latency.
    num_steps = 50 
    
    # --- EXECUTION ---
    
    # 1. Initialize position using the stable, blocking command (T:104)
    if not move_single_point_init(start):
        return
    
    # 2. Run the upward streaming motion using the fast T:1041 command
    print("\n--- Testing UPWARD Streaming Motion (FASTER) ---")
    linear_move(start, end, steps=num_steps)

    time.sleep(1.5)
    
    # 3. Test Downward Trajectory 
    print("\n--- Testing DOWNWARD Streaming Motion (FASTER) ---")
    linear_move(end, start, steps=num_steps) 

if __name__ == "__main__":
    main()
