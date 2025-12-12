#!/usr/bin/env python3
"""
detect_object_from_frame.py

- Loads frame.jpg
- Converts to HSV
- Thresholds using HSV range based on your measured values:
    H mean ~124, min=121, max=127
- Finds largest blob
- Draws a red dot at its centroid
- Saves an annotated image

Run:
    python3 detect_object_from_frame.py
"""

import cv2
import numpy as np

IMAGE_PATH = "frame.jpg"
OUTPUT_MASK = "frame_mask.jpg"
OUTPUT_ANN  = "frame_annotated.jpg"

# HSV range built from your measurement:
# H: 121–127  -> we'll use a bit of margin: 110–140
# S: 171–229 -> keep S relatively high
# V: 148–185 -> keep V moderately high
LOWER_HSV = np.array([110, 150, 120], dtype=np.uint8)
UPPER_HSV = np.array([140, 255, 255], dtype=np.uint8)


def main():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print("ERROR: could not load", IMAGE_PATH)
        return

    print("Loaded", IMAGE_PATH, "with shape", img.shape)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)

    # Clean mask a bit
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    cv2.imwrite(OUTPUT_MASK, mask)
    print("Saved mask to", OUTPUT_MASK)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No contours found. HSV range may need tweaking.")
        return

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print(f"Largest contour area: {area:.1f} pixels")

    if area < 100:
        print("Largest contour too small (likely noise).")
        return

    M = cv2.moments(largest)
    if M["m00"] == 0:
        print("Could not compute centroid (m00=0).")
        return

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    print(f"Centroid pixel (u, v) = ({cx}, {cy})")

    annotated = img.copy()
    cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)        # red dot at centroid
    cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2) # green outline

    cv2.imwrite(OUTPUT_ANN, annotated)
    print("Saved annotated image to", OUTPUT_ANN)


if __name__ == "__main__":
    main()
