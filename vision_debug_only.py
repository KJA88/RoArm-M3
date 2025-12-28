import cv2
import json
import numpy as np
from pathlib import Path
from picamera2 import Picamera2

PROJECT_ROOT = Path.cwd()
HSV_PATH = PROJECT_ROOT / "lessons/03_vision_color_detection/profiles/green_triangle.json"

print("Loading HSV from:", HSV_PATH)

with open(HSV_PATH) as f:
    hsv = json.load(f)

LOWER = np.array(hsv["lower"], np.uint8)
UPPER = np.array(hsv["upper"], np.uint8)
MIN_AREA = hsv.get("min_area", 300)

print("HSV DATA:", hsv)

IMG_W, IMG_H = 1280, 720

picam2 = Picamera2()
cfg = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_W, IMG_H)}
)
picam2.configure(cfg)
picam2.start()

# LOCK auto exposure / white balance
picam2.set_controls({
    "AeEnable": False,
    "AwbEnable": False
})

kernel = np.ones((5,5), np.uint8)

print("VISION DEBUG (HEADLESS) — press CTRL+C to quit")

try:
    while True:
        frame = picam2.capture_array()
        hsv_img = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        mask = cv2.inRange(hsv_img, LOWER, UPPER)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not cnts:
            continue

        c = max(cnts, key=cv2.contourArea)
        area = int(cv2.contourArea(c))

        if area < MIN_AREA:
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            continue

        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        print(f"TRACKING px=({u},{v}) area={area}", flush=True)

except KeyboardInterrupt:
    pass

finally:
    picam2.stop()
