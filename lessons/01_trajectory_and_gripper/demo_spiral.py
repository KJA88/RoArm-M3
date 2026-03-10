#!/usr/bin/env python3
"""
Spiral Demo — Converging In / Out

Demonstrates smooth continuous convergence and expansion.
Excellent for showcasing control quality and calibration stability.
"""

import time
import json
import math
import serial

# =========================
# Configuration
# =========================
PORT = "/dev/ttyUSB0"
BAUD = 115200
GRIPPER_RAD = 3.0

CX, CY, CZ = 240.0, 0.0, 260.0
R_START = 120.0
R_END   = 20.0
STEPS = 360
DT = 0.03

# =========================
# Serial Helpers
# =========================
def open_serial(port, baud):
    ser = serial.Serial(port=port, baudrate=baud, timeout=0.1)
    time.sleep(2.0)
    return ser

def send_json(ser, msg):
    ser.write((json.dumps(msg) + "\n").encode("utf-8"))

# =========================
# Spiral Demo
# =========================
def run_spiral_demo(ser):
    print("\n--- Starting Spiral Demo ---")

    # Move to start
    send_json(ser, {
        "T": 104,
        "x": CX + R_START,
        "y": CY,
        "z": CZ,
        "t": 0, "r": 0, "g": GRIPPER_RAD, "spd": 0.5
    })
    time.sleep(1.5)

    # Spiral IN
    for i in range(STEPS):
        alpha = i / STEPS
        r = (1 - alpha) * R_START + alpha * R_END
        theta = 2.0 * math.pi * alpha * 3.0

        send_json(ser, {
            "T": 1041,
            "x": CX + r * math.cos(theta),
            "y": CY + r * math.sin(theta),
            "z": CZ,
            "t": 0, "r": 0, "g": GRIPPER_RAD
        })
        time.sleep(DT)

    # Spiral OUT
    for i in range(STEPS):
        alpha = i / STEPS
        r = (1 - alpha) * R_END + alpha * R_START
        theta = 2.0 * math.pi * alpha * 3.0

        send_json(ser, {
            "T": 1041,
            "x": CX + r * math.cos(theta),
            "y": CY + r * math.sin(theta),
            "z": CZ,
            "t": 0, "r": 0, "g": GRIPPER_RAD
        })
        time.sleep(DT)

# =========================
# Main
# =========================
def main():
    ser = open_serial(PORT, BAUD)
    send_json(ser, {"T": 210, "cmd": 1})
    time.sleep(0.5)

    run_spiral_demo(ser)

    send_json(ser, {"T": 105})
    ser.close()
    print("Done.")

if __name__ == "__main__":
    main()
