#!/usr/bin/env python3

import serial
import json
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

print("RoArm Serial Console Ready")
print("Type JSON commands and press ENTER")
print("Example: {\"T\":210,\"cmd\":1}")

while True:
    try:
        cmd = input("CMD > ")
        ser.write((cmd + "\n").encode())
    except KeyboardInterrupt:
        break

ser.close()
