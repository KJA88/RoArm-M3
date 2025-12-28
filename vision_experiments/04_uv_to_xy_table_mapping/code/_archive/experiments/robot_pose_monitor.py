#!/usr/bin/env python3
"""
Robot Pose Monitor

Continuously prints robot (x, y, z)
Run this in Terminal 1 while jogging the robot manually
"""

import json
import time
import serial

ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

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

print("\n=== ROBOT POSE MONITOR ===")
print("Ctrl+C to exit\n")

try:
    while True:
        pose = get_pose()
        if pose:
            x, y, z = pose
            print(f"\rX={x:7.1f}  Y={y:7.1f}  Z={z:7.1f}", end="")
        else:
            print("\rNo feedback", end="")
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nExiting pose monitor")

finally:
    ser.close()
