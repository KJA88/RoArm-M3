#!/usr/bin/env python3
"""
Milestone 09-B: Firmware Pose After Streaming Motion

GOAL:
After forcing physical motion via trajectory streaming,
compare firmware-reported pose against custom FK.
"""

import time
import json
import math
import serial
import numpy as np

# --- SERIAL CONFIG ---
PORT = "/dev/ttyUSB0"
BAUD = 115200

# --- ARM GEOMETRY (from Milestone 08) ---
L1 = 238.0
L2 = 316.0
TCP_OFFSET = 120.0  # along wrist X

def forward_kinematics(joints):
    s, e = joints
    x = L1 * math.cos(s) + L2 * math.cos(s + e)
    z = L1 * math.sin(s) + L2 * math.sin(s + e)
    return x, z

def get_firmware_status(ser):
    ser.write(b'{"T":105}\n')
    for _ in range(15):
        line = ser.readline().decode(errors="ignore")
        if "{" in line:
            try:
                return json.loads(line[line.find("{"):])
            except:
                pass
    return None

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(1.5)

    print("\n--- M09-B: Stream → Read Pose → Compare ---")

    # 1. FORCE MOTION (stream to known location)
    print("\n[STEP 1] Streaming to known pose...")
    stream_cmds = [
        {"T":1041, "x":300, "y":0, "z":250, "t":0, "r":0, "g":3.0},
        {"T":1041, "x":320, "y":0, "z":230, "t":0, "r":0, "g":3.0},
        {"T":1041, "x":340, "y":0, "z":210, "t":0, "r":0, "g":3.0},
    ]

    for cmd in stream_cmds:
        ser.write((json.dumps(cmd) + "\n").encode())
        time.sleep(0.05)

    time.sleep(1.5)  # allow motion to settle

    # 2. READ FIRMWARE POSE
    print("[STEP 2] Reading firmware pose...")
    status = get_firmware_status(ser)
    if not status:
        print("ERROR: No firmware response")
        return

    fx = status.get("x")
    fz = status.get("z")
    s = status.get("s")
    e = status.get("e")

    print(f"Firmware Pose -> X:{fx:.2f} Z:{fz:.2f}")
    print(f"Firmware Joints -> Shoulder:{s:.3f} Elbow:{e:.3f}")

    # 3. CUSTOM FK
    cx, cz = forward_kinematics((s, e))
    print(f"Custom FK     -> X:{cx:.2f} Z:{cz:.2f}")

    # 4. ERROR
    err = math.hypot(fx - cx, fz - cz)
    print(f"\nPosition Error: {err:.2f} mm")

    ser.close()
    print("\n[OK] M09-B comparison complete.")

if __name__ == "__main__":
    main()
