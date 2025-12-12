#!/usr/bin/env python3
"""
camera_color_localize_picam2.py

- Uses Picamera2 (libcamera) to grab ONE frame
- Uses the HSV thresholds we derived from inspect_center_hsv.py
- Finds the largest blob of that color
- Prints centroid pixel (u, v)
- Saves:
    - raw frame
    - mask
    - annotated image
"""

import time
import cv2
import numpy as np

from picamera2 import Picamera2

IMAGE_RAW  = "cam_live_frame.jpg"
IMAGE_MASK = "cam_live_mask.jpg"
IMAGE_ANN  = "cam_live_annotated.jpg"

# HSV range based on your measured object color:
# H: 121–127 -> margin -> 110–140
# S: 171–229 -> S >= 150
# V: 148–185 -> V >= 120
LOWER_HSV = np.array([110, 150, 120], dtype=np.uint8)
UPPER_HSV = np.array([140, 255, 255], dtype=np.uint8)


def main():
    picam2 = Picamera2()

    # 1280x720 is plenty and not too heavy
    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)
    picam2.start()

    # let auto-exposure / white balance settle a bit
    time.sleep(1.0)

    # capture_array returns RGB
    frame_rgb = picam2.capture_array()
    picam2.close()

    # Convert to BGR for OpenCV
    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    print("Captured frame shape:", frame.shape)
    cv2.imwrite(IMAGE_RAW, frame)
    print("Saved raw frame to", IMAGE_RAW)

    # 1) HSV + mask
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    cv2.imwrite(IMAGE_MASK, mask)
    print("Saved mask to", IMAGE_MASK)

    # 2) Contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No contours found — object might be out of view or HSV off.")
        return

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print(f"Largest contour area: {area:.1f} pixels")

    if area < 100:
        print("Largest contour too small (likely noise).")
        return

    M = cv2.moments(largest)
    if M["m00"] == 0:
        print("Cannot compute centroid (m00=0).")
        return

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    print(f"Centroid pixel (u, v) = ({cx}, {cy})")

    # 3) Annotate
    annotated = frame.copy()
    cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)        # red dot
    cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2) # green outline

    h, w = annotated.shape[:2]
    cv2.drawMarker(annotated, (w // 2, h // 2), (255, 0, 0),
                   markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

    cv2.imwrite(IMAGE_ANN, annotated)
    print("Saved annotated frame to", IMAGE_ANN)


if __name__ == "__main__":
    main()
