#!/usr/bin/env python3
"""
Milestone 09: Custom IK vs Firmware IK

GOAL:
Compare a math-derived IK solution against firmware-reported
end-effector position for the same target poses.
"""

import math
import json
import time
import serial

# --- ARM GEOMETRY (from Milestone 08) ---
L1 = 238.0
L2 = 316.0

# --- SERIAL CONFIG ---
PORT = "/dev/ttyUSB0"
BAUD = 115200

def planar_ik(x, z):
    """Simple 2-link planar IK (shoulder + elbow)"""
    r = math.hypot(x, z)
    cos_e = (r**2 - L1**2 - L2**2) / (2 * L1 * L2)
    if abs(cos_e) > 1:
        return None

    e = math.acos(cos_e)
    s = math.atan2(z, x) - math.atan2(L2 * math.sin(e), L1 + L2 * math.cos(e))
    return {"shoulder": s, "elbow": e}

def get_firmware_pose(ser):
    ser.write(b'{"T":105}\n')
    for _ in range(10):
        line = ser.readline().decode(errors="ignore")
        if "{" in line:
            try:
                return json.loads(line[line.find("{"):])
            except:
                pass
    return None

if __name__ == "__main__":
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(1.0)

    test_targets = [
        {"name": "CENTER", "x": 300, "z": 200},
        {"name": "REACH",  "x": 450, "z": 150},
        {"name": "LOW",    "x": 250, "z": 120},
    ]

    print("\n--- Milestone 09: IK Comparison ---")

    for t in test_targets:
        print(f"\nTarget: {t['name']}  X={t['x']} Z={t['z']}")

        ik = planar_ik(t["x"], t["z"])
        if not ik:
            print("Custom IK: UNREACHABLE")
            continue

        print(f"Custom IK -> Shoulder:{ik['shoulder']:.3f}  Elbow:{ik['elbow']:.3f}")

        # Command firmware IK
        cmd = {
            "T": 101,
            "x": t["x"],
            "y": 0,
            "z": t["z"],
            "t": 0,
            "spd": 500
        }
        ser.write((json.dumps(cmd) + "\n").encode())
        time.sleep(1.5)

        pose = get_firmware_pose(ser)
        if pose:
            fx = pose.get("x")
            fz = pose.get("z")
            dx = fx - t["x"]
            dz = fz - t["z"]
            err = math.hypot(dx, dz)
            print(f"Firmware -> X:{fx:.1f} Z:{fz:.1f}  Error:{err:.2f}mm")
        else:
            print("Firmware: NO RESPONSE")

    ser.close()
    print("\n[OK] IK comparison complete.")
