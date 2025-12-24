#!/usr/bin/env python3
"""
Lesson 01 (Expansion) – Combined Demo Suite

This script runs three distinct movement patterns consecutively:
1. Circle/Helix Demo (1 loop)
2. Line Trajectory (3 repeats)
3. Lissajous Figure-8 (3 repeats)

Location: /home/kallen/RoArm/lessons/01_trajectory_and_gripper/03_combined_demo_suite.py
"""

import time
import json
import serial
import math
import numpy as np

# =========================
# Configuration
# =========================
PORT = "/dev/ttyUSB0"
BAUD = 115200
GRIPPER_RAD = 3.0  # radians (1.08 to 3.14 range)
CANDLE_POSE = {"x": 0, "y": 0, "z": 400, "t": 0, "r": 0}

# =========================
# Serial Helpers
# =========================
def open_serial(port, baud):
    ser = serial.Serial(port=port, baudrate=baud, timeout=0.1)
    time.sleep(2.0) # ESP32 settle time
    return ser

def send_json(ser, msg):
    line = json.dumps(msg) + "\n"
    ser.write(line.encode("utf-8"))

# =========================
# Demo 1: Circle / Helix
# =========================
def run_circle_helix_demo(ser):
    print("\n--- Starting Circle/Helix Demo ---")
    CX, CY, CZ = 235.0, 0.0, 234.0
    R, AMP, STEPS, DT = 100.0, 20.0, 180, 0.04

    # Move to start (T:104 - Blocking)
    send_json(ser, {"T": 104, "x": 285.0, "y": 0.0, "z": 234.0, "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5})
    time.sleep(2.0)

    for i in range(STEPS):
        theta = 2.0 * math.pi * (i / STEPS)
        # T:1041 - Non-blocking direct control
        send_json(ser, {
            "T": 1041,
            "x": CX + R * math.cos(theta),
            "y": CY + R * math.sin(theta),
            "z": CZ + AMP * math.sin(theta),
            "t": 0.0, "r": 0.0, "g": GRIPPER_RAD
        })
        time.sleep(DT)

# =========================
# Demo 2: Line Trajectory (3x)
# =========================
def run_line_demo(ser, iterations=3):
    print(f"\n--- Starting Line Demo ({iterations} repeats) ---")
    START_XYZ = np.array([220.0, -60.0, 300.0])
    END_XYZ   = np.array([220.0,  60.0, 300.0])
    STEPS, DT = 120, 0.04

    for iteration in range(iterations):
        print(f"  Line iteration {iteration + 1}...")
        # Move to start of line (T:104)
        send_json(ser, {"T": 104, "x": float(START_XYZ[0]), "y": float(START_XYZ[1]), "z": float(START_XYZ[2]), "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5})
        time.sleep(1.5)

        for i in range(STEPS + 1):
            alpha = i / STEPS
            p = (1.0 - alpha) * START_XYZ + alpha * END_XYZ
            send_json(ser, {"T": 1041, "x": float(p[0]), "y": float(p[1]), "z": float(p[2]), "t": 0, "r": 0, "g": GRIPPER_RAD})
            time.sleep(DT)

# =========================
# Demo 3: Lissajous Figure-8 (3x)
# =========================
def run_lissajous_demo(ser, iterations=3):
    print(f"\n--- Starting Lissajous Demo ({iterations} repeats) ---")
    CX, CY, CZ = 240.0, 0.0, 250.0
    WIDTH, HEIGHT, LENGTH = 80.0, 40.0, 50.0
    STEPS, DT = 300, 0.03

    for iteration in range(iterations):
        print(f"  Lissajous iteration {iteration + 1}...")
        # Move to center of figure-8 (T:104)
        send_json(ser, {"T": 104, "x": CX, "y": CY, "z": CZ, "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5})
        time.sleep(1.5)

        for i in range(STEPS + 1):
            phi = 2.0 * math.pi * (i / STEPS)
            cmd = {
                "T": 1041,
                "x": round(CX + (LENGTH/2) * math.cos(phi), 2),
                "y": round(CY + WIDTH * math.sin(2 * phi), 2),
                "z": round(CZ + HEIGHT * math.sin(phi), 2),
                "t": round(0.3 * math.cos(phi), 2),
                "r": 0, "g": GRIPPER_RAD
            }
            send_json(ser, cmd)
            time.sleep(DT)

# =========================
# Main Routine
# =========================
def main():
    try:
        ser = open_serial(PORT, BAUD)
        # Torque ON (T:210)
        send_json(ser, {"T": 210, "cmd": 1})
        time.sleep(0.5)

        # Run the demo sequence
        run_circle_helix_demo(ser)
        run_line_demo(ser, iterations=3)
        run_lissajous_demo(ser, iterations=3)

        # Final Return to Safe Pose
        print("\nAll tasks complete. Returning to Candle Pose...")
        send_json(ser, {"T": 104, "x": CANDLE_POSE["x"], "y": CANDLE_POSE["y"], "z": CANDLE_POSE["z"], 
                        "t": CANDLE_POSE["t"], "r": CANDLE_POSE["r"], "g": GRIPPER_RAD, "spd": 0.5})
        time.sleep(2.0)
        
        # Request final feedback (T:105)
        send_json(ser, {"T": 105})
        ser.close()
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
