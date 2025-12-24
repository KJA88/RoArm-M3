#!/usr/bin/env python3
"""
Lesson 01 (Expansion) – Advanced Lissajous Streaming

This script streams a 3D Lissajous curve (figure-8) using T=1041.
It demonstrates real-time parametric path planning and dynamic wrist orientation.
"""

import time
import json
import serial
import math

# =========================
# Serial helpers
# =========================

def open_serial(port, baud):
    ser = serial.Serial(port=port, baudrate=baud, timeout=0.1)
    time.sleep(2.0)  # allow ESP32 to settle
    return ser

def send_json(ser, msg):
    line = json.dumps(msg) + "\n"
    ser.write(line.encode("utf-8"))

# =========================
# Parameters
# =========================

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Center of the workspace (Safe zone for RoArm-M3)
CX, CY, CZ = 240.0, 0.0, 250.0

# Trajectory scale
WIDTH  = 80.0   # Y-axis swing (Left/Right)
HEIGHT = 40.0   # Z-axis swing (Up/Down)
LENGTH = 50.0   # X-axis depth (Forward/Back)

STEPS = 300     # total points in the path
DT = 0.03       # seconds between points (~33 Hz)
GRIPPER_RAD = 3.0

# =========================
# Main
# =========================

def main():
    print("=== Advanced Lissajous Streaming ===")
    print(f"Streaming at {1/DT:.1f} Hz...")

    try:
        ser = open_serial(PORT, BAUD)

        # 1. Enable torque
        send_json(ser, {"T": 210, "cmd": 1})
        time.sleep(0.5)

        # 2. Move to start pose (Blocking T=104)
        print("Moving to start pose...")
        send_json(ser, {
            "T": 104, "x": CX, "y": CY, "z": CZ,
            "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5
        })
        time.sleep(2.0)

        # 3. Stream Lissajous Trajectory (T=1041)
        print("Executing 3D figure-8 pattern...")
        for i in range(STEPS + 1):
            phi = 2.0 * math.pi * (i / STEPS)

            # Parametric Equations for Figure-8
            tx = CX + (LENGTH/2) * math.cos(phi)
            ty = CY + WIDTH * math.sin(2 * phi)
            tz = CZ + HEIGHT * math.sin(phi)
            
            # Dynamic Tilt: Wrist pitches up/down based on Z-velocity
            tt = 0.3 * math.cos(phi)

            cmd = {
                "T": 1041,
                "x": round(tx, 2), "y": round(ty, 2), "z": round(tz, 2),
                "t": round(tt, 2), "r": 0, "g": GRIPPER_RAD
            }

            send_json(ser, cmd)
            time.sleep(DT)

        # 4. Return to Safe / Candle Pose
        print("Returning to Candle Pose...")
        send_json(ser, {"T": 104, "x": 0, "y": 0, "z": 400, "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5})
        time.sleep(2.0)

        ser.close()
        print("Done!")

    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    main()
