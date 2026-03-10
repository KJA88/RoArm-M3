#!/usr/bin/env python3
"""
Milestone 02: Mechanical Truths — Revolute Joint Limit Calibration

PURPOSE:
- Human-verified mechanical limits
- DATA COLLECTION ONLY
- No enforcement
- No IK
- No trajectories
- No gripper / tool behavior
- Revolute joints ONLY: 2 (Shoulder), 3 (Elbow), 4 (Wrist)

This script MUST NOT be reused beyond Milestone 02.
"""

import serial
import json
import time
from datetime import datetime
from pathlib import Path

# ================= CONFIG =================

PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.2
SETTLE_TIME = 0.5

OUTPUT_PATH = Path("/home/kallen/RoArm/core/calibration/joint_limits.json")

# Vendor ranges are EXPLORATION BOUNDS ONLY
JOINTS = {
    2: {"name": "Shoulder", "min": -1.5707963, "max":  1.5707963},
    3: {"name": "Elbow",    "min": -0.8726646, "max":  3.1415926},
    4: {"name": "Wrist",    "min": -1.5707963, "max":  1.5707963},
}

# ========================================


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))


def move_single_joint(ser, joint_id, rad):
    """
    Issue authority ONLY to the joint under test.
    No other joints are referenced or reset.
    """
    cmd = {"T": 102, "spd": 0, "acc": 0}

    if joint_id == 2:
        cmd["shoulder"] = rad
    elif joint_id == 3:
        cmd["elbow"] = rad
    elif joint_id == 4:
        cmd["wrist"] = rad
    else:
        raise ValueError("Invalid joint for Milestone 02")

    send(ser, cmd)
    time.sleep(SETTLE_TIME)

    print(f"→ COMMANDED {JOINTS[joint_id]['name']} = {rad:.3f} rad")


def write_limits(data):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    log(f"Limits written to {OUTPUT_PATH}")


def main():
    ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    time.sleep(0.3)
    log("Serial connection established")

    # Torque ON (explicit, no automation beyond this)
    send(ser, {"T": 210, "cmd": 1})
    time.sleep(0.3)
    log("Torque ENABLED")

    inc = float(input("\nEnter jog increment (rad), e.g. 0.05 or 0.1: ").strip())

    limits_out = {}

    for joint_id, info in JOINTS.items():
        name = info["name"]
        jmin = info["min"]
        jmax = info["max"]
        mid = round((jmin + jmax) / 2, 3)

        print("\n" + "=" * 60)
        print(f"Calibrating Joint {joint_id}: {name}")
        print(f"Vendor exploration range: [{jmin}, {jmax}] rad")
        print(f"Starting at MID: {mid} rad")
        print("=" * 60)

        move_single_joint(ser, joint_id, mid)

        joint_limits = {}

        for label, direction in [("NEGATIVE", -1), ("POSITIVE", +1)]:
            log(f"Testing {label} direction")
            current = mid

            print("Controls: k = jog | ENTER = lock | q = abort")

            while True:
                key = input(f"[{label}] k=step | ENTER=lock | q=quit: ").strip().lower()

                if key == "q":
                    log("ABORTED by user")
                    write_limits(limits_out)
                    ser.close()
                    return

                if key == "":
                    joint_limits[label.lower()] = round(current, 3)
                    log(f"{label} limit recorded: {current:.3f} rad")
                    move_single_joint(ser, joint_id, mid)
                    break

                if key == "k":
                    next_pos = round(current + direction * inc, 3)

                    if not (jmin <= next_pos <= jmax):
                        print("BLOCKED: Outside vendor exploration bounds")
                        continue

                    current = next_pos
                    move_single_joint(ser, joint_id, current)

        limits_out[str(joint_id)] = {
            "name": name,
            "negative_limit": joint_limits["negative"],
            "positive_limit": joint_limits["positive"],
            "units": "radians",
            "verified_by": "human",
            "milestone": "02_mechanical_truth",
        }

    print("\n=== MECHANICAL TRUTH VERIFIED ===")
    for jid, data in limits_out.items():
        print(f"Joint {jid} ({data['name']}):")
        print(f"  NEGATIVE: {data['negative_limit']} rad")
        print(f"  POSITIVE: {data['positive_limit']} rad")

    write_limits(limits_out)
    log("Milestone 02 complete. Torque remains ENABLED.")
    ser.close()


if __name__ == "__main__":
    main()
