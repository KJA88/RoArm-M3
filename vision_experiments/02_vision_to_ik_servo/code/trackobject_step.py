#!/usr/bin/env python3
"""
Lesson 05 — Definitive Stepwise XY Vision Servo (EYE-TO-HAND)
STABLE VERSION: Added physical movement verification and diagnostic logging.
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# =========================================================
# 1. TUNABLE PARAMETERS & CALIBRATION
# =========================================================
GAIN     = 0.18     
MAX_STEP = 15.0     
DEADBAND = 4        

OFFSET_U = 0        
OFFSET_V = 0        

MIN_X, MAX_X = 150, 450 # Expanded X range for better reach
MIN_Y, MAX_Y = -250, 250
SAFE_Z       = 250  

GRIPPER_SAFE = 3.0  
ROBOT_PORT   = "/dev/ttyUSB0"
BAUD         = 115200

# =========================================================
# 2. INITIALIZATION
# =========================================================
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"format": "RGB888", "size": (1280, 720)})
picam2.configure(config)
picam2.start()
time.sleep(0.5)

U0, V0 = (1280 // 2) + OFFSET_U, (720 // 2) + OFFSET_V

try:
    with open("lessons/03_vision_color_detection/hsv_config.json") as f:
        hsv_cfg = json.load(f)
    LOWER = np.array(hsv_cfg["lower"], dtype=np.uint8)
    UPPER = np.array(hsv_cfg["upper"], dtype=np.uint8)
except:
    print("CRITICAL: Run Lesson 03 first.")
    exit()

try:
    ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()
except Exception as e:
    print(f"CRITICAL: Serial Error: {e}")
    exit()

# =========================================================
# 3. CONTROL FUNCTIONS
# =========================================================
def get_robot_xyz():
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')
    t0 = time.time()
    while time.time() - t0 < 1.0:
        line = ser.readline()
        if not line: continue
        try:
            msg = json.loads(line.decode(errors="ignore"))
            if msg.get("T") == 1051:
                return msg["x"], msg["y"], msg["z"]
        except: continue
    return None

def move_xy(x, y, z):
    tx, ty = np.clip(x, MIN_X, MAX_X), np.clip(y, MIN_Y, MAX_Y)
    cmd = {"T": 1041, "x": round(tx, 2), "y": round(ty, 2), "z": round(z, 2), "t": 0, "r": 0, "g": GRIPPER_SAFE}
    ser.write(json.dumps(cmd).encode() + b"\n")
    time.sleep(0.1) # Wait for firmware to ingest

# =========================================================
# 4. PRE-FLIGHT & MAIN LOOP
# =========================================================
print("\n=== Lesson 05: Diagnostic Visual Servo ===")
start_pos = get_robot_xyz()
if start_pos:
    cx, cy, cz = start_pos
    if abs(cz - SAFE_Z) > 5:
        print(f"[PRE-FLIGHT] Adjusting Z to {SAFE_Z}...")
        move_xy(cx, cy, SAFE_Z)
        time.sleep(2.0)
else:
    print("CRITICAL: Robot not responding.")
    exit()

try:
    while True:
        key = input("\n> [ENTER] to step (q to quit): ").strip().lower()
        if key == "q": break

        # A. Vision
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LOWER, UPPER)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("[NO DETECTION]")
            continue

        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] == 0: continue
        u, v = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])

        # Debug Image
        debug_img = frame.copy()
        cv2.drawMarker(debug_img, (U0, V0), (255, 0, 0), cv2.MARKER_CROSS, 30, 2)
        cv2.circle(debug_img, (u, v), 10, (0, 0, 255), -1)
        cv2.imwrite("last_snapshot.jpg", cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))

        # B. Logic
        du, dv = u - U0, v - V0
        if abs(du) < DEADBAND and abs(dv) < DEADBAND:
            print(f"Centered at ({u},{v})")
            continue

        sx, sy = np.clip(dv * GAIN, -MAX_STEP, MAX_STEP), np.clip(du * GAIN, -MAX_STEP, MAX_STEP)

        # C. Actuation with Verification
        before = get_robot_xyz()
        if before:
            print(f"Current Pos: X={before[0]:.1f}, Y={before[1]:.1f}")
            move_xy(before[0] + sx, before[1] + sy, SAFE_Z)
            
            # Wait for physical move to complete
            time.sleep(0.8) 
            
            after = get_robot_xyz()
            if after:
                print(f"New Pos:     X={after[0]:.1f}, Y={after[1]:.1f}")
                print(f"Vision Obj: ({u},{v}) | Pix Error: ({du},{dv})")
        else:
            print("[ERROR] Serial feedback failed.")

except KeyboardInterrupt:
    pass
finally:
    ser.close()
    picam2.close()