#!/usr/bin/env python3
"""
Robot Keyboard Jog Controller (LINE-BASED, SIMPLE)

Controls (type letter + ENTER):
W = +X
S = -X
A = +Y
D = -Y
R = +Z
F = -Z
Q = quit
"""

import json
import time
import serial

ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

STEP_XY = 5.0
STEP_Z  = 5.0

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)

def get_pose():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith('{"T":1051'):
            try:
                msg = json.loads(line)
                return msg["x"], msg["y"], msg["z"]
            except:
                pass
    return None

def move_xyz(x, y, z):
    cmd = {
        "T": 1041,
        "x": round(x, 1),
        "y": round(y, 1),
        "z": round(z, 1),
        "t": 0,
        "r": 0,
        "g": 3.0
    }
    ser.write((json.dumps(cmd) + "\n").encode())

print("\n=== ROBOT KEYBOARD JOG ===")
print("Type W/S/A/D/R/F + ENTER to move. Q to quit.\n")

pose = get_pose()
if pose is None:
    print("ERROR: Robot feedback failed")
    ser.close()
    exit(1)

x, y, z = pose

try:
    while True:
        print(f"Current: X={x:.1f}  Y={y:.1f}  Z={z:.1f}")
        key = input("> ").strip().lower()

        if key == "q":
            break
        elif key == "w":
            x += STEP_XY
        elif key == "s":
            x -= STEP_XY
        elif key == "a":
            y += STEP_XY
        elif key == "d":
            y -= STEP_XY
        elif key == "r":
            z += STEP_Z
        elif key == "f":
            z -= STEP_Z
        else:
            print("Unknown key")
            continue

        move_xyz(x, y, z)
        time.sleep(0.1)

finally:
    ser.close()
    print("Exited jog controller")
