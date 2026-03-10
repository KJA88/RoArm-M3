#!/usr/bin/env python3
"""
MechanicalSupervisor (PHASE 2 - AUTHORITATIVE)
Strictly for Task-Space (X,Y,Z) control using the T:104 protocol.
"""
import serial
import json
import time
import sys

class MechanicalSupervisor:
    def __init__(self, port="/dev/ttyUSB0", baud=115200):
        try:
            self.ser = serial.Serial(port, baud, timeout=1.0)
            time.sleep(2.0)
            # Engage Torque
            self._write_raw({"T": 210, "cmd": 1})
            # Switch to Coordinate Mode
            self._write_raw({"T": 111, "cmd": 1})
            print("[M05] Supervisor Online: Task-Space Authority Established.")
        except Exception as e:
            print(f"BOOT ERROR: {e}"); sys.exit(1)

    def _write_raw(self, cmd):
        payload = json.dumps(cmd) + "\n"
        self.ser.write(payload.encode("ascii"))
        # We read the response but don't obsess over it; the firmware is blind.
        return self.ser.readline().decode("ascii", errors="ignore").strip()

    def move_to_pose(self, x, y, z, pitch):
        """Standard Move: Uses the protocol we proved works."""
        cmd = {"T": 104, "x": x, "y": y, "z": z, "t": pitch, "spd": 250}
        print(f"[M05] Executing Move -> X:{x} Y:{y} Z:{z}")
        self._write_raw(cmd)
        time.sleep(2.0) # Hardware travel time

    def close(self):
        self.ser.close()
        print("[M05] Connection Closed.")