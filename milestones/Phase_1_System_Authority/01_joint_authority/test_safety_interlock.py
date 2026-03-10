#!/usr/bin/env python3
"""
TEST SCRIPT: Safety Interlock Validation
Location: /home/kallen/RoArm/milestones/01_joint_authority/test_safety_interlock.py

This script specifically tests if the Supervisor refuses a dangerous 
gripper command (0.5 rad) while allowing a safe one (1.5 rad).
"""

import json
import time
import serial
from datetime import datetime

# --- CONFIGURATION ---
PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_If00-port0"
BAUD = 115200
GRIPPER_MIN_RAD = 1.1 # The "Hardware Law"

class SafetyTestSupervisor:
    def __init__(self):
        self.ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Test Link Established.")

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def send(self, cmd):
        msg = json.dumps(cmd) + "\n"
        self.ser.write(msg.encode())
        return self.ser.readline().decode().strip()

    def move_gripper(self, rad):
        # The Interlock Check
        if rad < GRIPPER_MIN_RAD:
            self.log(f"!!! INTERLOCK TRIGGERED: {rad}rad is DANGEROUS. Command Blocked.")
            return
        
        self.log(f"Command SAFE: Sending {rad}rad to Gripper.")
        self.send({"T": 101, "joint": 6, "rad": rad, "spd": 50})

if __name__ == "__main__":
    test = SafetyTestSupervisor()
    
    print("\n--- STARTING SAFETY TEST ---")
    
    # 1. Test the "Dangerous" command
    print("\nSTEP 1: Attempting to close gripper to 0.5 rad (Should be BLOCKED)...")
    test.move_gripper(0.5)
    
    time.sleep(1)
    
    # 2. Test the "Safe" command
    print("\nSTEP 2: Attempting to close gripper to 1.5 rad (Should be ALLOWED)...")
    test.move_gripper(1.5)
    
    print("\n--- TEST COMPLETE ---")
