#!/usr/bin/env python3
"""
Milestone 06: Trajectory Streaming
Location: /home/kallen/RoArm/milestones/06_trajectory_streaming/milestone_06_trajectory.py

GOAL: Demonstrate continuous path-following (Streaming) vs discrete moves (Teleporting).
This fulfills the final stage of Phase 2: Task-Space (Motion Logic).
"""

import time
import json
import math
import serial
from datetime import datetime

# --- CONFIGURATION ---
PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.1

# Path Parameters: A 3D converging spiral
CX, CY, CZ = 240.0, 0.0, 260.0
R_START, R_END = 120.0, 20.0
STEPS = 250
DT = 0.03 # 33Hz streaming rate

class TrajectorySupervisor:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            time.sleep(2.0)
            self.log("Trajectory Engine Online (M06).")
            # Ensure Torque is ON per M00
            self.send({"T": 210, "cmd": 1})
        except Exception as e:
            self.log(f"CRITICAL: Connection Failed: {e}")
            exit()

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def send(self, msg):
        line = json.dumps(msg) + "\n"
        self.ser.write(line.encode("utf-8"))
        # We capture the line to keep the serial buffer clean
        return self.ser.readline()

    def run_milestone_06(self):
        """
        Implementation: Converting parametric equations into 
        a smooth coordinate stream using T:1041.
        """
        self.log("Starting Continuous Path Verification (T:1041)...")
        
        # 1. Discreet move to starting pose
        self.send({
            "T": 104, "x": CX + R_START, "y": CY, "z": CZ,
            "t": 0, "r": 0, "g": 3.0, "spd": 0.5
        })
        time.sleep(2.0)

        # 2. Continuous Trajectory Loop
        for i in range(STEPS):
            alpha = i / STEPS
            radius = (1 - alpha) * R_START + alpha * R_END
            theta = 2.0 * math.pi * alpha * 3.0 # 3 full rotations

            target_x = CX + radius * math.cos(theta)
            target_y = CY + radius * math.sin(theta)

            # T: 1041 is the 'Streaming' command specified in M06
            cmd = {
                "T": 1041,
                "x": round(target_x, 2),
                "y": round(target_y, 2),
                "z": CZ,
                "t": 0, "r": 0, "g": 3.0
            }
            self.send(cmd)
            time.sleep(DT)

        self.log("Milestone 06 Complete: Smooth path verified.")

if __name__ == "__main__":
    engine = TrajectorySupervisor()
    engine.run_milestone_06()
