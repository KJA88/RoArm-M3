#!/usr/bin/env python3
"""
Milestone 01: Joint Authority & Safety

Scope:
- Joint-space ONLY
- No IK
- No task-space
- Raw serial control
- Visual confirmation is sufficient

Purpose:
Prove intentional, safe joint control and enforce real mechanical limits.
"""

import time
import json
import serial
from datetime import datetime

# ---------------- CONFIGURATION ----------------
PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.2

# Empirically verified gripper hard stop
GRIPPER_SAFE_LIMIT = 1.1  # radians

# ------------------------------------------------


class RoArmSupervisor:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            time.sleep(0.3)
            self.log(f"Serial connection established on {PORT}")

            # Enable torque on startup
            self.set_torque(True)
            time.sleep(0.3)

            # Move to known neutral joint pose
            self.log("Setting neutral joint pose...")
            self.set_neutral_pose()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            raise SystemExit(1)

    # ---------------- UTILITY ----------------

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def send(self, msg):
        line = json.dumps(msg) + "\n"
        self.ser.write(line.encode("ascii"))
        return self.ser.readline().decode("ascii", errors="ignore").strip()

    # ---------------- HARDWARE CONTROL ----------------

    def set_torque(self, enabled: bool):
        state = 1 if enabled else 0
        self.log(f"Torque {'ENABLED' if enabled else 'DISABLED'}")
        return self.send({"T": 210, "cmd": state})

    def set_neutral_pose(self):
        """
        Sets all joints to 0 radians using joint-space control.
        """
        cmd = {
            "T": 102,
            "base": 0.0,
            "shoulder": 0.0,
            "elbow": 0.0,
            "wrist": 0.0,
            "roll": 0.0,
            "hand": 3.0,   # open gripper safely
            "spd": 0.5,
            "acc": 0
        }
        self.send(cmd)
        time.sleep(2.0)

    def move_single_joint(self, joint_id: int, rad: float):
        """
        Move a single joint by joint index.
        Joint IDs:
            1 = base
            2 = shoulder
            3 = elbow
            4 = wrist
            5 = roll
            6 = hand (gripper)
        """

        # Gripper safety interlock
        if joint_id == 6 and rad < GRIPPER_SAFE_LIMIT:
            self.log(
                f"INTERLOCK: Blocked gripper command {rad} rad "
                f"(limit {GRIPPER_SAFE_LIMIT})"
            )
            return

        cmd = {
            "T": 101,
            "joint": joint_id,
            "rad": rad,
            "spd": 50
        }
        self.send(cmd)

    # ---------------- TEST LOGIC ----------------

    def run_readiness_test(self):
        self.log("Starting joint readiness sweep...")

        # Test Base, Shoulder, Elbow
        for joint_id in [1, 2, 3]:
            self.log(f"Testing Joint {joint_id}...")
            self.move_single_joint(joint_id, 0.3)
            time.sleep(1.0)
            self.move_single_joint(joint_id, 0.0)
            time.sleep(1.0)

        self.log("Milestone 01 COMPLETE: Joint authority verified.")

    # ---------------- CLEANUP ----------------

    def shutdown(self):
        self.log("Disabling torque and shutting down.")
        self.set_torque(False)
        self.ser.close()


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    arm = RoArmSupervisor()
    try:
        arm.run_readiness_test()
    finally:
        arm.shutdown()
