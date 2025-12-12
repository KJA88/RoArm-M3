#!/usr/bin/env python3
"""
Simple one-shot camera test using Picamera2 + OpenCV.

What it does:
  - Opens the IMX708 camera
  - Waits 2 seconds for auto-exposure to settle
  - Captures one frame into a NumPy array
  - Prints the shape (H, W, C)
  - Saves it as frame.jpg in the current folder
"""

from picamera2 import Picamera2
import cv2
import time


def main():
    picam2 = Picamera2()

    # Use a still configuration (good quality single frame)
    config = picam2.create_still_configuration()
    picam2.configure(config)

    print("Starting camera...")
    picam2.start()
    time.sleep(2.0)  # let auto exposure / focus settle a bit

    print("Capturing frame...")
    frame = picam2.capture_array()  # this is a NumPy array (H, W, 3)

    print("Frame shape:", frame.shape)
    print("Saving to frame.jpg ...")
    cv2.imwrite("frame.jpg", frame)

    picam2.close()
    print("Done.")


if __name__ == "__main__":
    main()
