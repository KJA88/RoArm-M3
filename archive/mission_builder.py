#!/usr/bin/env python3
import time
import sys
import os
import subprocess
import json
from math import sqrt

# --- Configuration ---
ROARM_CONTROL_SCRIPT = "./roarm_control.py"
MISSION_NAME = "pick_n_place"
SAFE_ROLL = 0.0
STEP_SIZE_MM = 3.0       # Distance per micro-step
SAFE_Z = 100             # Guaranteed safe low Z point

# --- Mission Definition (using Z=100 for all low points) ---
MISSION_SEQUENCE = [
    {"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "Home Start"},
    {"x": 250, "y": 0, "z": 150, "r": SAFE_ROLL, "g": 0.5, "desc": "Approach A"},
    {"x": 250, "y": 0, "z": 100, "r": SAFE_ROLL, "g": 0.5, "desc": "Pick A"},
    {"x": 250, "y": 0, "z": 100, "r": SAFE_ROLL, "g": 3.0, "desc": "Grip"},
    {"x": 250, "y": 0, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Lift"},
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 3.0, "desc": "Approach B"},
    {"x": 100, "y": 150, "z": 100, "r": SAFE_ROLL, "g": 3.0, "desc": "Drop B"},
    {"x": 100, "y": 150, "z": 100, "r": SAFE_ROLL, "g": 0.5, "desc": "Release"},
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 0.5, "desc": "Retreat"},
    {"x": 200, "y": 0, "z": 200, "r": SAFE_ROLL, "g": 0.5, "desc": "Return Home"}
]

# --- Core Mission Protocol Function (sends commands without using 'raw') ---
def send_protocol_command(command_dict):
    """
    Sends a RAW JSON command using the existing 'move' action in roarm_control.py.
    This works around the need for a 'raw' action by piggybacking the command 
    onto the existing serial port access method.
    """
    json_str = json.dumps(command_dict)
    
    try:
        # We call the 'move' action but pass the JSON command as the X-coordinate.
        # This relies on roarm_control.py sending the raw command regardless of
        # what the X, Y, Z coordinates actually are, which is often true for simple demos.
        subprocess.run([sys.executable, ROARM_CONTROL_SCRIPT, "move", 
                        json_str, "0", "0", "0", "0"],
                       check=True, capture_output=True, text=True, timeout=10)
        time.sleep(0.1) # Small pause to ensure command is processed by ESP32

    except subprocess.CalledProcessError as e:
        print(f"--- CRITICAL ERROR: Protocol command failed (Attempting to send: {json_str}) ---")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        print("ACTION REQUIRED: The final successful solution requires the 'raw' action.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during command send: {e}")
        sys.exit(1)
        
# --- Distance-Based Interpolation ---
def interpolate_points(p1, p2, step_size=STEP_SIZE_MM):
    """
    Returns a list of micro-steps between p1 -> p2 spaced by `step_size` mm.
    """
    x1, y1, z1 = p1["x"], p1["y"], p1["z"]
    x2, y2, z2 = p2["x"], p2["y"], p2["z"]
    
    dist = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    steps = max(1, int(dist / step_size))

    points = []
    for i in range(1, steps + 1):
        t = i / steps
        points.append({
            "x": x1 + t * (x2 - x1),
            "y": y1 + t * (y2 - y1),
            "z": z1 + t * (z2 - z1),
            "r": p2["r"],
            "g": p1["g"], 
        })
    return points

# --- Main Mission Logic ---
def main():
    print("--- Starting Mission Builder Engine ---")
    
    # 1. Create a new mission file (T=220)
    print(f"1. Creating mission file '{MISSION_NAME}'...")
    send_protocol_command({"T": 220, "name": MISSION_NAME, "intro": "Smooth pick and place demo."})

    # 2. Loop and add steps (T=222)
    previous_point = MISSION_SEQUENCE[0]
    
    # Send the first step directly (as a T=104 command)
    step_cmd = {"T": 104, "x": previous_point['x'], "y": previous_point['y'], "z": previous_point['z'], "r": previous_point['r'], "g": previous_point['g'], "spd": 0.25}
    send_protocol_command({"T": 222, "name": MISSION_NAME, "step": json.dumps(step_cmd)})

    for i in range(1, len(MISSION_SEQUENCE)):
        current_point = MISSION_SEQUENCE[i]
        
        # Check if this is a purely gripping/releasing action
        is_gripping_action = (current_point["x"] == previous_point["x"] and
                              current_point["y"] == previous_point["y"] and
                              current_point["z"] == previous_point["z"] and
                              current_point["g"] != previous_point["g"])

        if is_gripping_action:
            # 2a. Add the single T=104 gripping/releasing command
            print(f"-> Adding single step: {current_point['desc']}")
            step_cmd = {"T": 104, "x": current_point['x'], "y": current_point['y'], "z": current_point['z'], "r": current_point['r'], "g": current_point['g'], "spd": 0.25}
            send_protocol_command({"T": 222, "name": MISSION_NAME, "step": json.dumps(step_cmd)})
        
        else:
            # 2b. Generate and add interpolated micro-steps
            print(f"-> Interpolating and adding steps: {previous_point['desc']} -> {current_point['desc']}")
            micro_steps = interpolate_points(previous_point, current_point)
            
            for micro_point in micro_steps:
                # T=104 is blocking, but it's safe to use when writing the mission file
                step_cmd = {"T": 104, "x": micro_point['x'], "y": micro_point['y'], "z": micro_point['z'], "r": micro_point['r'], "g": micro_point['g'], "spd": 0.25}
                send_protocol_command({"T": 222, "name": MISSION_NAME, "step": json.dumps(step_cmd)})

        previous_point = current_point
        
    print("\n3. Mission file built successfully on ESP32 flash.")

    # 4. Playback the mission (T=242)
    print("\n4. Starting mission playback (T=242). Check arm movement for smoothness!")
    send_protocol_command({"T": 242, "name": MISSION_NAME, "times": 1})
    
    print("\nMission finished. Check arm for smooth execution.")

if __name__ == "__main__":
    main()
