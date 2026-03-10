#!/usr/bin/env python3
"""
Milestone 04: Task-Space Authority
Location: /home/kallen/RoArm/milestones/04_understanding_ik/milestone_04_supervisor.py

INTEGRATION: This script takes your Spiral/Lissajous math and wraps it in 
the "Deterministic Handshake" (M03) and "Safety Floor" logic.
"""

import time
import json
import serial
import math
from datetime import datetime

# --- CONFIGURATION ---
PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.5

# Physical Limits
Z_SAFETY_FLOOR = 20.0  # mm above table
GRIPPER_MIN_RAD = 1.1

class TaskSpaceSupervisor:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            time.sleep(2.0)
            self.log("Task-Space Supervisor Online.")
            self.set_torque(True)
        except Exception as e:
            self.log(f"CRITICAL: Connection Failed: {e}")
            exit()

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def send_and_wait(self, msg):
        """M03: Deterministic Handshake Logic"""
        line = json.dumps(msg) + "\n"
        self.ser.write(line.encode("ascii"))
        receipt = self.ser.readline().decode("ascii", errors="ignore").strip()
        return receipt

    def set_torque(self, enabled):
        return self.send_and_wait({"T": 210, "cmd": 1 if enabled else 0})

    def move_xyz(self, x, y, z, t=0, r=0, g=3.0, interpolate=True):
        """
        M04 Implementation: Validated Task-Space Move.
        Ensures the arm cannot violate the 'Safety Floor'.
        """
        # Safety Check: Floor
        if z < Z_SAFETY_FLOOR:
            self.log(f"BLOCKING MOVE: Z={z} violates Safety Floor!")
            return None
        
        # Safety Check: Gripper
        if g < GRIPPER_MIN_RAD:
            g = GRIPPER_MIN_RAD

        cmd = {
            "T": 1041 if interpolate else 104,
            "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
            "t": round(t, 2), "r": round(r, 2), "g": round(g, 2)
        }
        
        if not interpolate:
            cmd["spd"] = 0.5
            
        return self.send_and_wait(cmd)

    def run_validated_spiral(self):
        """Uses your proven Spiral math within the Supervisor's safety gates."""
        self.log("Running Validated Spiral Path...")
        CX, CY, CZ = 240.0, 0.0, 260.0
        R_START, R_END = 120.0, 20.0
        STEPS = 180 # Clean verification run
        
        for i in range(STEPS):
            alpha = i / STEPS
            r = (1 - alpha) * R_START + alpha * R_END
            theta = 2.0 * math.pi * alpha * 3.0
            
            tx = CX + r * math.cos(theta)
            ty = CY + r * math.sin(theta)
            
            # The 'move_xyz' method handles the JSON and the handshake
            self.move_xyz(tx, ty, CZ)
            time.sleep(0.03)

if __name__ == "__main__":
    arm = TaskSpaceSupervisor()
    arm.run_validated_spiral()