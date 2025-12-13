#!/usr/bin/env python3
"""
camera_snap.py

- Capture a single frame from Picamera2
- Save as frame.jpg in the current directory
- Uses the SAME color pipeline as camera_color_localize_picam2.py
"""

import time
import cv2
from picamera2 import Picamera2

OUTPUT = "frame.jpg"

def main():
    picam2 = Picamera2()

    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)

    # Let auto white balance and exposure settle
    picam2.set_controls({"AwbEnable": True})
    picam2.start()
    time.sleep(1.0)

    # IMPORTANT:
    # With format="RGB888", capture_array() returns a BGR-style array
    # suitable for OpenCV. Do NOT swap channels again.
    frame = picam2.capture_array()
    picam2.close()

    h, w = frame.shape[:2]
    print(f"Captured frame: {w}x{h}")
    cv2.imwrite(OUTPUT, frame)
    print("Saved", OUTPUT)

if __name__ == "__main__":
    main()
