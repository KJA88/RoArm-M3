#!/usr/bin/env python3

import cv2
from picamera2 import Picamera2
from hsv_utils import load_hsv_config

# Load visual classes
chess_cfg = load_hsv_config(
    "lessons/03_vision_color_detection/hsv/chess_white.json"
)

tool_cfg = load_hsv_config(
    "lessons/03_vision_color_detection/hsv/tool_marker.json"
)

def detect_centroid(frame, cfg):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, cfg["hsv_min"], cfg["hsv_max"])

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < cfg["min_area"]:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    return (
        int(M["m10"] / M["m00"]),
        int(M["m01"] / M["m00"])
    )

# Camera setup
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

print("Dual-color detection test (Ctrl+C to exit)")

try:
    while True:
        frame = picam2.capture_array()

        chess_uv = detect_centroid(frame, chess_cfg)
        tool_uv  = detect_centroid(frame, tool_cfg)

        print(f"Chess: {chess_uv} | Tool: {tool_uv}")

except KeyboardInterrupt:
    pass

picam2.close()
print("Exited cleanly.")
