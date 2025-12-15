#!/usr/bin/env python3
"""
cam_robot_log_samples.py  (Lesson 04)

Purpose:
- On each ENTER:
    1) Detect colored object -> (u,v) pixel centroid (HSV threshold)
    2) Ask robot for feedback -> (x,y,z)
    3) Append CSV row: timestamp,u,v,x,y,z
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2

try:
    import serial
except ImportError:
    serial = None


# ============================================================
# PATHS (EXPLICIT, NO GUESSING)
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent          # RoArm/lessons/04_camera_robot_calib
LESSONS_DIR = SCRIPT_DIR.parent                       # RoArm/lessons
REPO_ROOT = LESSONS_DIR.parent                        # RoArm

HSV_PATH = REPO_ROOT / "lessons/03_vision_color_detection/hsv_config.json"
CSV_PATH = SCRIPT_DIR / "cam_robot_samples.csv"
DEBUG_DIR = SCRIPT_DIR / "debug"


# ============================================================
# CAMERA
# ============================================================

def init_camera(size=(1280, 720)) -> Picamera2:
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": size}
    )
    picam2.configure(config)
    picam2.set_controls({"AwbEnable": True, "AfMode": 2})
    picam2.start()
    time.sleep(0.8)
    return picam2


def capture_frame(picam2: Picamera2) -> np.ndarray:
    frame = picam2.capture_array()
    if frame is None:
        raise RuntimeError("Camera returned None frame")
    return frame


# ============================================================
# HSV + DETECTION
# ============================================================

def load_hsv_config(path: Path):
    cfg = json.loads(path.read_text())
    lower = np.array(cfg["lower"], dtype=np.uint8)
    upper = np.array(cfg["upper"], dtype=np.uint8)
    return lower, upper


def find_largest_blob(bgr, lower, upper):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, 1)
    mask = cv2.dilate(mask, kernel, 2)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None, mask, 0

    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < 50:
        return None, mask, len(contours)

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None, mask, len(contours)

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return (cx, cy, c), mask, len(contours)


def annotate(frame, blob):
    out = frame.copy()
    h, w = out.shape[:2]

    cv2.drawMarker(out, (w // 2, h // 2), (255, 0, 0),
                   cv2.MARKER_CROSS, 20, 2)

    if blob:
        cx, cy, c = blob
        cv2.drawContours(out, [c], -1, (0, 255, 0), 2)
        cv2.circle(out, (cx, cy), 6, (0, 0, 255), -1)
        cv2.putText(out, f"(u,v)=({cx},{cy})",
                    (cx + 10, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 255), 2)
    return out


# ============================================================
# ROBOT SERIAL
# ============================================================

class RoArmSerial:
    def __init__(self, port="/dev/ttyUSB0", baud=115200):
        if serial is None:
            raise RuntimeError("pyserial not installed")
        self.ser = serial.Serial(port, baudrate=baud, timeout=0.2)
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()

    def send(self, obj):
        msg = json.dumps(obj) + "\n"
        self.ser.write(msg.encode())

    def read_json(self, timeout=1.5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self.ser.readline()
            if not line:
                continue
            try:
                return json.loads(line.decode(errors="ignore"))
            except Exception:
                continue
        return None

    def get_xyz(self):
        self.send({"T": 105})
        while True:
            msg = self.read_json()
            if msg and msg.get("T") == 1051:
                return float(msg["x"]), float(msg["y"]), float(msg["z"])


# ============================================================
# CSV
# ============================================================

def ensure_csv(path: Path):
    if path.exists():
        return
    with path.open("w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "u", "v", "x", "y", "z"])


def append_csv(path, u, v, x, y, z):
    ts = datetime.now().isoformat(timespec="seconds")
    with path.open("a", newline="") as f:
        csv.writer(f).writerow([ts, u, v, x, y, z])


# ============================================================
# MAIN
# ============================================================

def main():
    if not HSV_PATH.exists():
        print("ERROR: HSV config not found:")
        print(" ", HSV_PATH)
        print("Run Lesson 03 first.")
        return

    DEBUG_DIR.mkdir(exist_ok=True)
    ensure_csv(CSV_PATH)

    lower, upper = load_hsv_config(HSV_PATH)

    print("\n=== Lesson 04: Camera → Robot Sample Logger ===")
    print("HSV:", HSV_PATH)
    print("CSV:", CSV_PATH)
    print("\nControls:")
    print("  ENTER -> capture sample")
    print("  q     -> quit\n")

    picam2 = init_camera()
    robot = RoArmSerial()

    count = 0

    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "q":
                break

            frame = capture_frame(picam2)
            blob, mask, _ = find_largest_blob(frame, lower, upper)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            cv2.imwrite(str(DEBUG_DIR / f"{ts}_raw.jpg"), frame)
            cv2.imwrite(str(DEBUG_DIR / f"{ts}_mask.jpg"), mask)

            if not blob:
                cv2.imwrite(str(DEBUG_DIR / f"{ts}_annotated.jpg"),
                            annotate(frame, None))
                print("[NO DETECTION]")
                continue

            cx, cy, _ = blob
            x, y, z = robot.get_xyz()

            append_csv(CSV_PATH, cx, cy, x, y, z)
            count += 1

            ann = annotate(frame, blob)
            cv2.imwrite(str(DEBUG_DIR / f"{ts}_annotated.jpg"), ann)

            print(f"[OK #{count}] u,v=({cx},{cy}) x,y,z=({x:.2f},{y:.2f},{z:.2f})")

    finally:
        picam2.close()
        robot.close()


if __name__ == "__main__":
    main()
