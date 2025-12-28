#!/usr/bin/env python3
"""
Lesson 06: Final Pick and Place
Uses the calibration matrix to grab an object in one shot.
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial
import os

# =========================================================
# 1. SETUP & PATHS
# =========================================================
HOME = os.path.expanduser("~")
MATRIX_PATH = os.path.join(HOME, "RoArm/lessons/06_transform_and_depth/calibration_matrix.npy")
HSV_PATH    = os.path.join(HOME, "RoArm/lessons/03_vision_color_detection/hsv_config.json")

# HEIGHT SETTINGS (Adjust these based on your table)
SAFE_Z   = 300  # Height while moving
PICK_Z   = 125  # Height to reach the table surface
GRIP_OPEN  = 0.0
GRIP_CLOSE = 2.5 # Adjust based on your object size

ROBOT_PORT = "/dev/ttyUSB0"
BAUD       = 115200

# =========================================================
# 2. CORE FUNCTIONS
# =========================================================

def load_resources():
    if not os.path.exists(MATRIX_PATH) or not os.path.exists(HSV_PATH):
        print("Missing Matrix or HSV config!")
        return None, None, None
    
    M = np.load(MATRIX_PATH)
    with open(HSV_PATH, 'r') as f:
        hsv = json.load(f)
    return M, np.array(hsv['lower']), np.array(hsv['upper'])

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.05)

def send_cmd(cmd):
    ser.write((json.dumps(cmd) + "\n").encode())
    time.sleep(0.1)

# =========================================================
# 3. MAIN EXECUTION
# =========================================================
M, hsv_min, hsv_max = load_resources()
if M is None: exit()

picam2 = Picamera2()
config = picam2.create_still_configuration(main={"format": "RGB888", "size": (1280, 720)})
picam2.configure(config)
picam2.start()

print("\n=== Lesson 06: Autonomous Pick and Place ===")
print("Move the object into view. Press Ctrl+C to stop.")

try:
    # 1. Torque ON and Move to Home/Search position
    send_cmd({"T": 210, "cmd": 1})
    send_cmd({"T": 1041, "x": 250, "y": 0, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_OPEN})
    time.sleep(1.0)

    while True:
        frame = picam2.capture_array()
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_frame, hsv_min, hsv_max)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 500:
                # Get Pixel Coordinates
                moments = cv2.moments(c)
                u = int(moments["m10"] / moments["m00"])
                v = int(moments["m01"] / moments["m00"])
                
                # TRANSFORM PIXELS TO MILLIMETERS
                # [u, v, 1] @ M = [target_x, target_y]
                target = np.dot([u, v, 1], M)
                tx, ty = target[0], target[1]
                
                print(f"Object detected at ({u}, {v}). Mapping to Robot: X={tx:.1f}, Y={ty:.1f}")

                # EXECUTE SEQUENCE
                print("1. Approach...")
                send_cmd({"T": 1041, "x": tx, "y": ty, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_OPEN})
                time.sleep(1.5)
                
                print("2. Pick...")
                send_cmd({"T": 1041, "x": tx, "y": ty, "z": PICK_Z, "t": 0, "r": 0, "g": GRIP_OPEN})
                time.sleep(1.0)
                send_cmd({"T": 1041, "x": tx, "y": ty, "z": PICK_Z, "t": 0, "r": 0, "g": GRIP_CLOSE})
                time.sleep(1.0)
                
                print("3. Lift...")
                send_cmd({"T": 1041, "x": tx, "y": ty, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_CLOSE})
                time.sleep(1.5)
                
                print("4. Drop...")
                send_cmd({"T": 1041, "x": 250, "y": 100, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_CLOSE}) # Move to side
                time.sleep(1.0)
                send_cmd({"T": 1041, "x": 250, "y": 100, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_OPEN})
                time.sleep(0.5)
                
                print("\nTask Complete. Waiting for next object...")
                # Move back to center search
                send_cmd({"T": 1041, "x": 250, "y": 0, "z": SAFE_Z, "t": 0, "r": 0, "g": GRIP_OPEN})
                time.sleep(2.0)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping...")
    send_cmd({"T": 210, "cmd": 0})
finally:
    ser.close()
    picam2.close()
