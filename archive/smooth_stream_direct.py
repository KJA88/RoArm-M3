#!/usr/bin/env python3
import sys
import os
import json
import serial
import numpy as np
import time
import subprocess # <<< THE CRITICAL MISSING IMPORT
from math import sqrt
from ik import inverse_kinematics

# --- Configuration (Must match your system settings) ---
PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
ROARM_CONTROL_SCRIPT = "./roarm_control.py"

G_OPEN   = 0.5
G_CLOSED = 3.0
# Optimized for maximum smoothness and speed
STEP_SIZE_RAD = 0.01    # Max joint motion per step (smoothness)
STREAM_HZ = 50          # Update frequency (50 times per second)
STREAM_DELAY = 1 / STREAM_HZ
BAUD = 115200

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
    steps = int(np.max(diff) / step_size) + 1 

    out = []
    for i in range(1, steps + 1):
        t = i / steps
        out.append(j1 + t * (j2 - j1))
    return out

# --- Direct Serial Sender Function ---
def send_t102_stream(s, joints):
    """Sends a T=102 command directly over the open serial port 's'."""
    cmd = {
        "T": 102,
        "base":     float(joints[0]),
        "shoulder": float(joints[1]),
        "elbow":    float(joints[2]),
        "wrist":    float(joints[3]),
        "roll":     float(joints[4]),
        "hand":     float(joints[5]),
        "spd": 0, 
        "acc": 0
    }
    
    pkt = json.dumps(cmd) + "\n"
    s.write(pkt.encode("utf-8"))
    s.flush()

def calculate_ik_and_stream(s, j1, p2):
    """
    Calculates IK for the target waypoint and streams interpolated steps live.
    """
    global LAST_JOINTS_5DOF

    target_xyz = np.array([p2["x"], p2["y"], p2["z"]], dtype=float)
    sol = inverse_kinematics(target_xyz, p2["r"], LAST_JOINTS_5DOF)
    
    if sol is None:
        print(f"[IK FAILED] Cannot move to ({p2['x']}, {p2['y']}, {p2['z']}). Skipping.")
        return j1

    LAST_JOINTS_5DOF = sol[:5]
    j2 = np.array([sol[0], sol[1], sol[2], sol[3], sol[4], p2["g"]])

    microsteps = interpolate_joints(j1, j2)
    print(f"-> Streaming {len(microsteps)} micro-steps...")
    
    for j_step in microsteps:
        # Send T=102 directly without subprocess overhead
        send_t102_stream(s, j_step) 
        time.sleep(STREAM_DELAY) # Maintain consistent stream rate

    return j2

# --- Main Streaming Loop ---
def main():
    global LAST_JOINTS_5DOF
    print(f"\n--- Starting DIRECT SERIAL Streaming Engine ({STREAM_HZ} Hz) ---")
    
    try:
        # Torque ON command relies on subprocess.run
        subprocess.run([sys.executable, ROARM_CONTROL_SCRIPT, "torque_on"], check=True, timeout=5)

        # 1. Open Serial Port ONCE
        with serial.Serial(PORT, BAUD, timeout=1) as s:
            
            # Use a zero array as the starting point for the first IK calculation
            initial_joints = np.array([0.0]*6) 

            # 2. Calculate and move to the initial start point (Home)
            j_start = calculate_ik_and_stream(s, initial_joints, MISSION_SEQUENCE[0])
            last_joints = j_start
            print("\nReady to stream motion.")
            
            # 3. Execute the entire mission sequence
            for i, point in enumerate(MISSION_SEQUENCE[1:]):
                print(f"Streaming step {i+2}/{len(MISSION_SEQUENCE)}: {point}")
                
                # Stream from the last successful joint position to the new target
                last_joints = calculate_ik_and_stream(s, last_joints, point)

    except serial.SerialException as e:
        print(f"\n[CRITICAL FAILURE] Could not open serial port {PORT}. Mission aborted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Mission aborted: {e}")
    finally:
        # Ensure arm is torqued off for safety
        # This subprocess call should now execute correctly
        subprocess.run([sys.executable, ROARM_CONTROL_SCRIPT, "torque_off"], check=False)
        print("\nStreaming finished.")


if __name__ == "__main__":
    main()
