# --- HOW THE PATH PLANNING SCRIPT WORKS ---
#
# The coordinates are not sent to the robot directly in one command. They are used by the Python code 
# to generate the trajectory:
#
# 1. Linear Interpolation (L.I.)
# The path_planner.py script uses L.I. (handled by the underlying roarm_control.py) to calculate 
# all the points that lie on the straight line between the mission waypoints.
#
# 2. Streaming Command (T:1041)
# The script sends a list of all waypoints to the robot's firmware. Because the T:1041 command is 
# non-blocking and the points are sent so quickly, the robot executes the movement as one continuous, 
# smooth straight line, even though it's receiving many separate commands.
#
# --------------------------------------------------------------------------
#

#!/usr/bin/env python3
import time
import sys
import os
import subprocess
import json

# --- Configuration ---
ROARM_CONTROL_SCRIPT = "./roarm_control.py"
SAFE_ROLL = 0.0 
DEFAULT_SPEED = 0.25 # Speed for the internal path planning

# --- Define the Sequential Mission Targets (Z=100 is the guaranteed safe low point) ---
# Gripper Values: G=0.5 is OPEN, G=3.0 is CLOSED
MISSION_SEQUENCE = [
    # 1. INITIAL SAFE POSITION (Gripper Open)
    {"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "INITIAL HOME POSITION"},
    
    # --- Pick Up Sequence ---
    {"x": 250, "y": 0, "z": 150, "r": SAFE_ROLL, "g": 0.5, "desc": "Approach A (Hover)"},
    {"x": 250, "y": 0, "z": 100,  "r": SAFE_ROLL, "g": 0.5, "desc": "Pick A (Down, Open) - Z=100 SAFE"},
    {"x": 250, "y": 0, "z": 100,  "r": SAFE_ROLL, "g": 3.0, "desc": "GRIP (Closed) - Z=100 SAFE"}, # Gripping action
    {"x": 250, "y": 0, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Lift (Safe Height)"},
    
    # --- Drop Off Sequence ---
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Approach B (Travel)"},
    {"x": 100, "y": 150, "z": 100,  "r": SAFE_ROLL, "g": 3.0, "desc": "Drop B (Lower) - Z=100 SAFE"},
    {"x": 100, "y": 150, "z": 100,  "r": SAFE_ROLL, "g": 0.5, "desc": "RELEASE (Open) - Z=100 SAFE"}, # Releasing action
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 0.5, "desc": "Retreat (Safe Height)"},
    
    # 2. FINAL HOME POSITION (Gripper Open)
    {"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "FINAL HOME POSITION"},
]

def execute_path_streaming(points):
    """
    Constructs and executes the path_planner command to stream all points.
    NOTE: path_planner.py expects a JSON list of points.
    """
    
    python_executable = sys.executable 
    
    # 1. Convert the Python list of dicts to a JSON string
    points_json_str = json.dumps(points)
    
    # 2. Build the command using 'stream' action
    command = [
        python_executable, 
        ROARM_CONTROL_SCRIPT,
        "stream",  # <-- The action to stream the path
        points_json_str,
        str(DEFAULT_SPEED)
    ]
    
    print(f"\n[Executing Path Stream] Sending {len(points)} waypoints...")
    
    try:
        # Run the command and capture output
        subprocess.run(command, capture_output=True, text=True, check=True, env=os.environ, timeout=60)
        print("\n--- Path Stream Complete ---")
        
    except subprocess.CalledProcessError as e:
        print(f"\n--- CRITICAL ERROR during Path Stream ---")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    print("--- RoArm Seamless Pick-and-Place Path Stream ---")
    
    # 1. Run Torque ON for safety before starting a mission
    print("\nAttempting to set Torque ON before mission start...")
    # FIX: Run the specific torque_on.py script instead of calling an action inside roarm_control.py
    subprocess.run([sys.executable, "./torque_on.py"], check=True, env=os.environ)

    # 2. Execute the entire mission path as a stream
    execute_path_streaming(MISSION_SEQUENCE)
    
    print("\nMission successfully executed with continuous motion.")

if __name__ == "__main__":
    main()
