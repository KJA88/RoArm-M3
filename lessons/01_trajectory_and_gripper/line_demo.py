#!/usr/bin/env python3
"""
Lesson 01 – Line Trajectory Streaming Demo

Streams a straight-line Cartesian trajectory between two XYZ points
using the RoArm-M3 firmware's internal IK (T=1041).

Self-contained:
- No project imports
- No package assumptions
- Safe to run directly
"""

import time
import json
import serial
import numpy as np

# =========================
# Serial helpers
# =========================

def open_serial(port, baud):
    ser = serial.Serial(
        port=port,
        baudrate=baud,
        timeout=0.1
    )
    time.sleep(2.0)  # allow ESP32 to settle
    return ser

def send_json(ser, msg):
    line = json.dumps(msg) + "\n"
    ser.write(line.encode("utf-8"))

# =========================
# User parameters
# =========================

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Line endpoints (mm)
START_XYZ = np.array([220.0, -60.0, 300.0])
END_XYZ   = np.array([220.0,  60.0, 300.0])

# Trajectory resolution
STEPS = 120          # number of points
DT = 0.04            # seconds between points (~25 Hz)

# Gripper (safe default)
GRIPPER_RAD = 3.0    # mostly closed, safe

# =========================
# Trajectory streaming
# =========================

def stream_line(ser, p0, p1, steps, dt):
    """
    Linearly interpolate from p0 to p1 and stream via T=1041.
    """
    for i in range(steps + 1):
        alpha = i / steps
        p = (1.0 - alpha) * p0 + alpha * p1

        cmd = {
            "T": 1041,
            "x": float(p[0]),
            "y": float(p[1]),
            "z": float(p[2]),
            "t": 0,
            "r": 0,
            "g": GRIPPER_RAD,
            "spd": 0.25
        }

        send_json(ser, cmd)
        time.sleep(dt)

# =========================
# Main
# =========================

def main():
    print("=== Lesson 01: Line Trajectory Streaming Demo ===")
    print(f"Start XYZ: {START_XYZ}")
    print(f"End   XYZ: {END_XYZ}")
    print(f"Steps={STEPS}, dt={DT}s")

    ser = open_serial(PORT, BAUD)

    # Enable torque
    send_json(ser, {"T": 210, "cmd": 1})
    time.sleep(0.5)

    # Move to start pose (blocking)
    send_json(ser, {
        "T": 104,
        "x": float(START_XYZ[0]),
        "y": float(START_XYZ[1]),
        "z": float(START_XYZ[2]),
        "t": 0,
        "r": 0,
        "g": GRIPPER_RAD,
        "spd": 0.25
    })

    time.sleep(1.0)

    # Stream straight line
    stream_line(ser, START_XYZ, END_XYZ, STEPS, DT)

    # Return to candle / safe pose
    send_json(ser, {
        "T": 104,
        "x": 0,
        "y": 0,
        "z": 400,
        "t": 0,
        "r": 0,
        "g": GRIPPER_RAD,
        "spd": 0.25
    })

    # Request one feedback packet (optional)
    send_json(ser, {"T": 105})

    print("Line trajectory demo complete.")

if __name__ == "__main__":
    main()
