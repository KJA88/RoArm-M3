#!/usr/bin/env python3
"""
Milestone 05: Firmware IK Implementation
Location: /home/kallen/RoArm/milestones/05_firmware_ik_validation/milestone_05_reachability.py

GOAL: Validate the arm's ability to reach specific coordinates accurately using T:104.
"""

import time
import json
import serial
from datetime import datetime

# --- CONFIGURATION ---
PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.5

class IKValidator:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            time.sleep(2.0)
            self.log("IK Validation System Online.")
            # Ensure Torque is ON
            self.send({"T": 210, "cmd": 1})
        except Exception as e:
            self.log(f"Connection Failed: {e}")
            exit()

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def send(self, msg):
        line = json.dumps(msg) + "\n"
        self.ser.write(line.encode("ascii"))
        return self.ser.readline().decode("ascii", errors="ignore").strip()

    def validate_coordinate(self, x, y, z):
        """
        Commands a move and then polls T:105 to verify the 
        arm's internal solver agreed with the target.
        """
        self.log(f"Testing Target -> X:{x} Y:{y} Z:{z}")
        
        # 1. Send Move Command (T:104)
        self.send({"T": 104, "x": x, "y": y, "z": z, "t": 0, "r": 0, "g": 3.0, "spd": 0.5})
        time.sleep(1.5) # Wait for physical travel
        
        # 2. Poll Status (T:105)
        response = self.send({"T": 105})
        try:
            data = json.loads(response)
            actual_x = data.get('x')
            actual_y = data.get('y')
            actual_z = data.get('z')
            
            # Calculate Error
            error = abs(x - actual_x) + abs(y - actual_y) + abs(z - actual_z)
            
            if error < 1.0:
                self.log(f"SUCCESS: Arrived at {actual_x}, {actual_y}, {actual_z} (Error: {error:.2f}mm)")
            else:
                self.log(f"FAILED: Positional Error too high! ({error:.2f}mm)")
        except:
            self.log("ERROR: Could not parse firmware feedback.")

    def run_validation_suite(self):
        # Test a sequence of points in the workspace
        points = [
            (250, 0, 250),
            (200, 100, 200),
            (200, -100, 200),
            (150, 0, 350)
        ]
        
        for p in points:
            self.validate_coordinate(p[0], p[1], p[2])
            time.sleep(0.5)

if __name__ == "__main__":
    validator = IKValidator()
    validator.run_validation_suite()
