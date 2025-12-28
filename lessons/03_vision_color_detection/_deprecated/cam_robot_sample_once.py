#!/usr/bin/env python3
"""
cam_robot_sample_once.py

One-shot sample:
  - Capture a frame with Picamera2
  - Detect the colored cylinder (HSV-based)
  - Get its centroid pixel (u, v)
  - Query the robot for T=1051 feedback (x, y, z)
  - Print both so we can later build (u, v) <-> (x, y, z) pairs
"""

import time
import json
import serial

import cv2
import numpy as np
from picamera2 import Picamera2

# ---------------- Camera / HSV config ----------------

IMAGE_RAW  = "sample_frame.jpg"
IMAGE_MASK = "sample_mask.jpg"
IMAGE_ANN  = "sample_annotated.jpg"

# HSV range from your measurement:
# H ≈ 121–127, S ≈ 171–229, V ≈ 148–185
# with some margin:
LOWER_HSV = np.array([110, 150, 120], dtype=np.uint8)
UPPER_HSV = np.array([140, 255, 255], dtype=np.uint8)

# ---------------- Robot config ----------------

PORT = "/dev/ttyUSB0"
BAUD = 115200


def capture_and_find_centroid():
    """Capture one frame with Picamera2 and return (u, v) and frame."""
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1.0)  # let AE/AWB settle a bit

    frame_rgb = picam2.capture_array()
    picam2.close()

    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(IMAGE_RAW, frame)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    cv2.imwrite(IMAGE_MASK, mask)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("No contours found in mask.")
        return None, None, frame

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print(f"Largest contour area: {area:.1f} pixels")

    if area < 100:
        print("Largest contour too small (noise).")
        return None, None, frame

    M = cv2.moments(largest)
    if M["m00"] == 0:
        print("Cannot compute centroid (m00=0).")
        return None, None, frame

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    annotated = frame.copy()
    cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)
    cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2)

    h, w = annotated.shape[:2]
    cv2.drawMarker(annotated, (w // 2, h // 2), (255, 0, 0),
                   markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

    cv2.imwrite(IMAGE_ANN, annotated)

    return cx, cy, annotated


def get_robot_feedback():
    """Send T=105 and return (x, y, z) from the T=1051 feedback."""
    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    time.sleep(0.2)

    # Request feedback packet
    cmd = {"T": 105}
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))
    time.sleep(0.1)

    lines = []
    for _ in range(5):
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            lines.append(line)
            print("UART:", line)

    ser.close()

    feedback = None
    for line in reversed(lines):
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("T") == 1051:
                feedback = obj
                break

    if feedback is None:
        print("No valid T=1051 feedback found.")
        return None, None, None

    x = feedback.get("x")
    y = feedback.get("y")
    z = feedback.get("z")
    return x, y, z


def main():
    print("Capturing frame and detecting object...")
    u, v, _ = capture_and_find_centroid()

    if u is None or v is None:
        print("No valid centroid; aborting sample.")
        return

    print(f"Detected centroid pixel (u, v) = ({u}, {v})")

    print("Requesting robot feedback (T=105)...")
    x, y, z = get_robot_feedback()

    if x is None:
        print("No valid robot feedback; aborting sample.")
        return

    print(f"Robot feedback XYZ = ({x:.1f}, {y:.1f}, {z:.1f})")

    print("\nSample pair:")
    print(f"  u = {u}, v = {v}")
    print(f"  x = {x:.1f}, y = {y:.1f}, z = {z:.1f}")


if __name__ == "__main__":
    main()
