#!/usr/bin/env python3
"""
Lesson 06 — Align + Descend (WORKING VERSION)

• Stable base yaw alignment
• Direct serial communication (like working circle demo)
• Smooth Z descent using T=1041
• Micro XY correction during descent
"""

import time
import json
import numpy as np
import cv2
from picamera2 import Picamera2
import serial
import os
import sys
import select

# ===============================
# PARAMETERS
# ===============================
PORT = "/dev/ttyUSB0"
BAUD = 115200

Z_TARGET   = -90.0
Z_STEP     = 5.0
DESCENT_DT = 0.10

GAIN_YAW   = 0.05
MAX_YAW_STEP = 3.0
DEADZONE   = 10

BASE_MIN  = -60
BASE_MAX  =  60

GRIPPER_OPEN = 1.08  # radians (open for picking)

# ===============================
# HSV CONFIG
# ===============================
HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv_config.json"
)
with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"])
HSV_MAX = np.array(hsv_cfg["upper"])

# ===============================
# SERIAL HELPERS
# ===============================
def send(ser, cmd):
    """Send JSON command over UART with newline"""
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))

def get_pose(ser):
    """Get current pose using T:105 command"""
    send(ser, {"T": 105})
    time.sleep(0.1)
    
    # Read multiple lines to find feedback
    for _ in range(10):
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line and '"T":1051' in line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
        time.sleep(0.05)
    return None

def stream_xyz(ser, x, y, z, t, r, g):
    """Stream XYZ position using T:1041 command"""
    send(ser, {
        "T": 1041,
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "t": float(t),
        "r": float(r),
        "g": float(g)
    })

# ===============================
# INIT SERIAL & ARM
# ===============================
ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.05)
time.sleep(0.5)

# TORQUE ON
send(ser, {"T": 210, "cmd": 1})
time.sleep(0.3)

# SAFE START POSE (T=102 - all joints in radians)
send(ser, {
    "T": 102,
    "base": 0,
    "shoulder": 0,
    "elbow": 1.5708,
    "wrist": 0,
    "roll": 0,
    "hand": GRIPPER_OPEN,
    "spd": 100,
    "acc": 0
})
time.sleep(2)

print("=== ARM INITIALIZED ===")

# ===============================
# CAMERA
# ===============================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format":"RGB888","size":(1280,720)}
)
picam2.configure(cfg)
picam2.start()
time.sleep(1)

# ===============================
# STATE
# ===============================
base_angle = 0.0
aligned_frames = 0
ALIGNED_FRAMES_REQUIRED = 5

print("=== ALIGN → DESCEND ===")
print("Type 'q' + Enter to quit")

# ===============================
# MAIN LOOP - ALIGNMENT PHASE
# ===============================
try:
    while True:
        # Check for quit
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.readline().strip().lower() == "q":
                break

        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

        contours,_ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            aligned_frames = 0
            time.sleep(0.05)
            continue

        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 600:
            aligned_frames = 0
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            aligned_frames = 0
            continue

        u = int(M["m10"]/M["m00"])
        v = int(M["m01"]/M["m00"])

        du = u - 640
        dv = v - 360

        print(f"Offset: du={du:4d}, dv={dv:4d}, base={base_angle:.1f}°")

        # Check if centered
        if abs(du) <= DEADZONE:
            aligned_frames += 1
            print(f"  Centered! ({aligned_frames}/{ALIGNED_FRAMES_REQUIRED})")
            
            if aligned_frames >= ALIGNED_FRAMES_REQUIRED:
                print("✓ ALIGNMENT COMPLETE")
                break
            
            time.sleep(0.05)
            continue
        else:
            aligned_frames = 0

        # Adjust base using T=121 (single joint angle control)
        step = np.sign(du) * min(MAX_YAW_STEP, abs(du)*GAIN_YAW)
        base_angle = np.clip(base_angle + step, BASE_MIN, BASE_MAX)
        
        send(ser, {
            "T": 121,
            "joint": 1,
            "angle": base_angle,
            "spd": 70,
            "acc": 10
        })
        time.sleep(0.1)

    # ===============================
    # DESCENT PHASE
    # ===============================
    print("\n=== STARTING DESCENT ===")
    pose = get_pose(ser)
    
    if not pose:
        print("ERROR: Could not get pose")
    else:
        x = pose["x"]
        y = pose["y"]
        z = pose["z"]
        t = pose["tit"]
        r = pose["r"]
        g = pose["g"]
        
        print(f"Starting: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")
        print(f"Target Z: {Z_TARGET:.1f}")

        step_count = 0
        while z > Z_TARGET:
            # Track object for micro-corrections
            frame = picam2.capture_array()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)
            contours,_ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                c = max(contours, key=cv2.contourArea)
                if cv2.contourArea(c) > 300:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        u = int(M["m10"]/M["m00"])
                        v = int(M["m01"]/M["m00"])
                        # Small XY corrections
                        x += np.clip((v-360)*0.01, -1, 1)
                        y += np.clip((u-640)*0.01, -1, 1)

            z -= Z_STEP
            step_count += 1
            print(f"  Step {step_count}: Z = {z:.1f} mm")
            stream_xyz(ser, x, y, z, t, r, g)
            time.sleep(DESCENT_DT)

        print("\n✓ DESCENT COMPLETE")
        print("Position held. Close gripper if needed.")

except KeyboardInterrupt:
    print("\n⚠ Interrupted")

finally:
    picam2.close()
    ser.close()
    print("Cleaned up. Exited.")