#!/usr/bin/env python3
"""
Capture one frame and find the largest bright, colorful blob.

What it does:
  - Captures a single frame from the IMX708
  - Converts to HSV
  - Thresholds for "high saturation + brightness" (any hue)
  - Finds the largest contour
  - Computes its centroid (cx, cy) in pixel coordinates
  - Computes offset from image center (dx, dy)
  - Draws a circle and crosshair on the blob
  - Saves result as big_object_out.jpg
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time


def main():
    picam2 = Picamera2()

    # Use a still configuration for good quality
    config = picam2.create_still_configuration()
    picam2.configure(config)

    print("Starting camera...")
    picam2.start()
    time.sleep(2.0)  # let exposure/white balance settle

    print("Capturing frame...")
    frame = picam2.capture_array()  # BGR image, shape (H, W, 3)
    print("Frame shape:", frame.shape)

    # Resize down so operations are cheaper
    scale = 0.5
    frame_small = cv2.resize(
        frame,
        (int(frame.shape[1] * scale), int(frame.shape[0] * scale)),
        interpolation=cv2.INTER_AREA,
    )

    # Convert to HSV
    hsv = cv2.cvtColor(frame_small, cv2.COLOR_BGR2HSV)

    # --- "Big bright colorful thing" mask ---
    # Any hue, but with decent saturation & brightness
    # tweak S/V thresholds if needed
    lower = np.array([0, 60, 60], dtype=np.uint8)
    upper = np.array([179, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)

    # Clean up mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out tiny specks
    contours = [c for c in contours if cv2.contourArea(c) > 500]

    if not contours:
        print("No big colorful object found. Try moving it closer / more in view.")
        out_name = "big_object_out.jpg"
        cv2.imwrite(out_name, frame_small)
        print(f"Saved raw frame to {out_name}")
        picam2.close()
        return

    # Largest contour = our object
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print("Largest contour area:", area)

    # Centroid
    M = cv2.moments(largest)
    if M["m00"] == 0:
        print("Contour had zero area in moments, skipping.")
        out_name = "big_object_out.jpg"
        cv2.imwrite(out_name, frame_small)
        print(f"Saved frame without markups to {out_name}")
        picam2.close()
        return

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    # Image center (in resized image)
    h, w = frame_small.shape[:2]
    center_x = w // 2
    center_y = h // 2

    dx = cx - center_x
    dy = cy - center_y

    print(f"Detected object at (cx, cy) = ({cx}, {cy}) in resized image.")
    print(f"Image center = ({center_x}, {center_y})")
    print(f"Offset from center: dx = {dx}, dy = {dy} (pixels)")

    # Full-res coords if we ever care later
    full_cx = int(cx / scale)
    full_cy = int(cy / scale)
    print(f"Approx. full-res coordinates: ({full_cx}, {full_cy})")

    # Draw marker
    cv2.circle(frame_small, (cx, cy), 10, (0, 255, 0), 2)
    cv2.drawMarker(
        frame_small,
        (cx, cy),
        (0, 255, 0),
        markerType=cv2.MARKER_CROSS,
        markerSize=20,
        thickness=2,
    )

    out_name = "big_object_out.jpg"
    cv2.imwrite(out_name, frame_small)
    print(f"Saved debug image with marker to {out_name}")

    picam2.close()
    print("Done.")


if __name__ == "__main__":
    main()
