#!/usr/bin/env python3
import time
import sys
import os
import subprocess
import json

# --- Configuration ---
ROARM_CONTROL_SCRIPT = "./roarm_control.py"
SAFE_ROLL = 0.0  # Maintain 0.0 Roll to minimize observed positional drift.

# --- Define the Mission Targets (XYZ and Gripper Position) ---
# Gripper Values: G=0.5 is OPEN, G=3.0 is CLOSED (Logic now reversed for correct action)
MISSION_POINTS = {
    # 1. Approach Point (Above Pickup Location, Gripper Open)
    "APPROACH_A": {"x": 250, "y": 0, "z": 150, "r": SAFE_ROLL, "g": 0.5, "desc": "Hovering above pickup (Open)"},
    
    # 2. Pickup Location (Z-safe, Gripper Open)
    "PICK_A":     {"x": 250, "y": 0, "z": 50,  "r": SAFE_ROLL, "g": 0.5, "desc": "Gripper down, open"},
    
    # 3. Gripping Action (Gripper Closed)
    "GRIP":       {"x": 250, "y": 0, "z": 50,  "r": SAFE_ROLL, "g": 3.0, "desc": "Gripper closed on object"},
    
    # 4. Lift (Move to Safe Transport Height, Gripper Closed)
    "LIFT":       {"x": 250, "y": 0, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Lifted to safe height"},
    
    # 5. Approach Drop Location (Above Drop Location, Gripper Closed)
    "APPROACH_B": {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Hovering above drop"},
    
    # 6. Drop Location (Gripper Closed)
    "DROP_B":     {"x": 100, "y": 150, "z": 50,  "r": SAFE_ROLL, "g": 3.0, "desc": "Lowered to drop point"},
    
    # 7. Release Action (Gripper Open)
    "RELEASE":    {"x": 100, "y": 150, "z": 50,  "r": SAFE_ROLL, "g": 0.5, "desc": "Object released"},
    
    # 8. Retreat (Move back to Safe Height, Gripper Open)
    "RETREAT":    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 0.5, "desc": "Retreat to safe height"},
}

def execute_move(point):
    """
    Constructs and executes the roarm_control.py command from a dictionary point.
    """
    python_executable = sys.executable 
    
    command = [
        python_executable, 
        ROARM_CONTROL_SCRIPT,
        "move",
        str(point["x"]),
        str(point["y"]),
        str(point["z"]),
        str(point["r"]),
        str(point["g"])
    ]
    
    print(f"\n[Executing: {point['desc']}] Command: {' '.join(command[2:])}")
    
    try:
        # Run the command and capture output
        subprocess.run(command, capture_output=True, text=True, check=True, env=os.environ, timeout=10)
        
    except subprocess.CalledProcessError as e:
        print(f"\n--- CRITICAL ERROR at {point['desc']} ---")
        print(f"Failed to move arm. Ensure the target XYZ is reachable.")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    print("--- RoArm Pick-and-Place Master Mission ---")
    
    # 1. Initial Position (Go to a known safe spot)
    execute_move({"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "INITIAL SAFE POSITION"})
    time.sleep(1)
    
    # 2. Execute the Mission Sequence
    print("\n--- Starting Pick-and-Place Sequence ---")
    
    for key, point in MISSION_POINTS.items():
        execute_move(point)
        time.sleep(2.5) # <-- INCREASED TIME to allow movement and settling

    # 3. Final Safe Position
    print("\n--- Mission Complete. Returning to Home. ---")
    execute_move({"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "FINAL HOME POSITION"})
    
    print("\nMaster Mission successfully executed.")

if __name__ == "__main__":
    main()

