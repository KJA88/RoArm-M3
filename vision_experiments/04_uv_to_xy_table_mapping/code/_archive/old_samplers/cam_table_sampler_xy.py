#!/usr/bin/env python3
"""
Camera → Table XY Sampler (Two-Terminal Workflow)

Terminal 1:
    robot_keyboard_jog.py  (YOU move the robot)

Terminal 2:
    this script            (ENTER logs a sample)

Logs:
    u, v, x, y

Also writes debug images:
    /tmp/debug_frame.jpg
    /tmp/debug_mask.jpg
"""

import json
import csv
import os
import sys
import select
import time
import numpy as np
import cv2
from picamera2 import Picamera2
import serial

# ============================================================
# PATHS
# ============================================================
CSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/07_xy_table_mapping/cam_table_samples.csv"
)

HSV_PATH = os.path.expanduser(
    "~/RoArm/lessons/03_vision_color_detection/hsv/tool_marker.json"
)

os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

# ============================================================
# ROBOT SERIAL
# ============================================================
ROBOT_PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(ROBOT_PORT, BAUD, timeout=0.1)

def get_robot_xy():
    """Query robot for current x,y"""
    ser.reset_input_buffer()
    ser.write(b'{"T":105}\n')

    for _ in range(10):
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith('{"T":1051'):
            try:
                msg = json.loads(line)
                return msg["x"], msg["y"]
            except Exception:
                pass
    return None

# ============================================================
# LOAD HSV
# ============================================================
if not os.path.exists(HSV_PATH):
    print(f"ERROR: HSV file not found: {HSV_PATH}")
    sys.exit(1)

with open(HSV_PATH, "r") as f:
    hsv_cfg = json.load(f)

HSV_MIN = np.array(hsv_cfg["lower"], dtype=np.uint8)
HSV_MAX = np.array(hsv_cfg["upper"], dtype=np.uint8)

print(f"Loaded HSV from: {HSV_PATH}")
print(f"HSV_MIN = {HSV_MIN}")
print(f"HSV_MAX = {HSV_MAX}")

# ============================================================
# CAMERA
# ============================================================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

# ============================================================
# CSV INIT
# ============================================================
new_file = not os.path.exists(CSV_PATH)

csv_file = open(CSV_PATH, "a", newline="")
writer = csv.writer(csv_file)

if new_file:
    writer.writerow(["u", "v", "x", "y"])

print("\n=== CAMERA → TABLE XY SAMPLER ===")
print("Move robot using robot_keyboard_jog.py")
print("Press ENTER to log one sample")
print("Press 'q' + ENTER to quit")
print("Debug images written to /tmp/\n")

# ============================================================
# MAIN LOOP
# ============================================================
try:
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip().lower()

            if key == "q":
                print("Quit requested")
                break

            # ENTER pressed
            elif key == "":
                frame = picam2.capture_array()

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, HSV_MIN, HSV_MAX)

                # ---- DEBUG OUTPUT (ALWAYS) ----
                cv2.imwrite("/tmp/debug_frame.jpg", frame)
                cv2.imwrite("/tmp/debug_mask.jpg", mask)
                print("Wrote /tmp/debug_frame.jpg and /tmp/debug_mask.jpg")

                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if not contours:
                    print("No marker detected")
                    continue

                c = max(contours, key=cv2.contourArea)

                area = cv2.contourArea(c)
                if area < 500:
                    print(f"Marker too small (area={area:.1f})")
                    continue

                M = cv2.moments(c)
                if M["m00"] == 0:
                    print("Invalid contour moments")
                    continue

                u = int(M["m10"] / M["m00"])
                v = int(M["m01"] / M["m00"])

                xy = get_robot_xy()
                if xy is None:
                    print("Robot feedback failed")
                    continue

                x, y = xy

                writer.writerow([u, v, x, y])
                csv_file.flush()

                print(
                    f"Logged: u={u:4d}, v={v:4d}  ->  x={x:7.1f}, y={y:7.1f}"
                )

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nKeyboardInterrupt")

finally:
    csv_file.close()
    picam2.close()
    ser.close()
    print("Exited cleanly")
