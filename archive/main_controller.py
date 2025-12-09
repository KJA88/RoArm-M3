import time
import json
import numpy as np
import subprocess
import os
import sys

# --- CRITICAL FIX: Set the path to the correct Python executable ---
VENV_PYTHON_PATH = '/home/kallen/RoArm/.venv/bin/python3'
# ------------------------------------------------------------------


def run_control_command(command_list, timeout=5, check=True):
    """Executes a command using roarm_control.py through the VENV interpreter."""
    
    # Prepend the correct Python executable path to the command list
    full_command = [VENV_PYTHON_PATH, './roarm_control.py'] + command_list
    
    try:
        # Use subprocess to run the command with the corrected path
        result = subprocess.run(
            full_command,
            check=check,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if result.stderr and "ERROR" in result.stderr.upper():
            print(f"[CRITICAL FAILURE] Control script reported error:\n{result.stderr}")
            run_control_command(['torque_off'], timeout=2, check=False)
            exit(1)
            
        return result
    except subprocess.CalledProcessError as e:
        # Added the usage message from the failure here to guide the user:
        if "Usage:" in e.stdout:
             print(f"[CRITICAL FAILURE] Mission aborted: Command structure error! Check arguments. Stderr: {e.stderr}")
        else:
             print(f"[CRITICAL FAILURE] Mission aborted: Command '{' '.join(full_command)}' returned non-zero exit status {e.returncode}.")
             print(f"Stdout: {e.stdout}")
        
        run_control_command(['torque_off'], timeout=2, check=False)
        exit(1)
    except subprocess.TimeoutExpired:
        print(f"[CRITICAL FAILURE] Mission aborted: Command '{' '.join(full_command)}' timed out after {timeout} seconds")
        run_control_command(['torque_off'], timeout=2, check=False)
        exit(1)
    except FileNotFoundError:
        print(f"[CRITICAL FAILURE] Mission aborted: Python interpreter not found at {VENV_PYTHON_PATH}. Check your VENV setup.")
        exit(1)


def load_mission(filename="waypoints.json"):
    """Loads waypoints from a JSON file."""
    if not os.path.exists(filename):
        print(f"Error: Mission file '{filename}' not found.")
        return None, None
        
    try:
        with open(filename, 'r') as f:
            mission_data = json.load(f)
            mission_name = mission_data.get("mission_name", "UNNAMED_MISSION")
            waypoints = mission_data.get("waypoints", [])
            return mission_name, waypoints
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filename}'. Check file format.")
        return None, None


def execute_mission(mission_name, waypoints):
    """Executes the sequence of waypoints."""
    
    print(f"\n--- Starting {mission_name} Velocity Controller (50 Hz) ---")
    
    # 1. Ensure Torque is ON before starting
    print("Attempting to enable motor torque...")
    run_control_command(['torque_on'])
    print("Torque ON successfully.")
    
    # 2. Iterate through waypoints
    for i, wp in enumerate(waypoints):
        x = wp.get("x")
        y = wp.get("y")
        z = wp.get("z")
        
        if x is None or y is None or z is None:
            print(f"Error: Waypoint {i+1} is missing x, y, or z coordinates. Skipping.")
            continue

        print(f"\nMoving to Waypoint {i+1}: X={x:.2f}, Y={y:.2f}, Z={z:.2f}...")
        
        # --- FIX APPLIED HERE: Removed the final 'speed' argument from the move command list ---
        # The usage is: move X Y Z R G (5 arguments)
        move_command = [
            'move',
            str(x),
            str(y),
            str(z),
            str(wp.get("roll_pitch", 0)),
            str(wp.get("roll_angle", 0)) 
            # Speed is not passed to the 'move' command, it's inherent or handled elsewhere.
        ]
        
        # Execute the move command
        run_control_command(move_command)
        print(f"Waypoint {i+1} reached.")
        time.sleep(wp.get("dwell_time", 1.0)) # Wait at the waypoint


    print("\n--- Mission Complete ---")
    
    # 3. Torque OFF after mission completion
    print("Mission complete. Attempting to disable motor torque...")
    run_control_command(['torque_off'])
    print("Torque OFF successfully.")


if __name__ == "__main__":
    mission_file = "waypoints.json"  # Default mission file
    
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        mission_file = sys.argv[1]
    else:
        print(f"No mission file specified. Loading default: {mission_file}")
        
    mission_name, waypoints = load_mission(mission_file)
    
    if waypoints:
        print(f"SUCCESS: Loaded Mission Name: {mission_name}")
        execute_mission(mission_name, waypoints)
    else:
        print("Mission could not be loaded or is empty. Aborting.")
