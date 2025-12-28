#!/usr/bin/env python3
"""
camera_snap.py (fixed, path-safe)

Always saves to:
  lessons/03_vision_color_detection/frame.jpg
"""

import time
import cv2
from pathlib import Path
from picamera2 import Picamera2

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT = SCRIPT_DIR / "frame.jpg"

def main():
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)

    picam2.set_controls({"AwbEnable": True, "AfMode": 2})  # AfMode=2 continuous AF
    picam2.start()
    time.sleep(1.0)

    frame = picam2.capture_array()
    picam2.close()

    h, w = frame.shape[:2]
    print(f"Captured frame: {w}x{h}")
    cv2.imwrite(str(OUTPUT), frame)
    print("Saved:", OUTPUT)

if __name__ == "__main__":
    main()
