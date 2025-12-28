#!/usr/bin/env python3
"""
Dual HSV Detection Test (Vision Only)

- Loads TWO HSV configs:
    - tool_marker.json
    - chess_white.json
- Captures ONE frame
- Detects both objects
- Prints (u, v) for each
- Saves annotated image

NO robot motion.
"""

import json
from pathlib import Path
import numpy as np
import cv2
from picamera2 import Picamera2

# ===============================
# PATHS
# ===============================
SCRIPT_DIR = Path(__file__).resolve().parent
HSV_DIR = SCRIPT_DIR / "hsv"

TOOL_HSV = HSV_DIR / "tool_marker.json"
OBJ_HSV  = HSV_DIR / "chess_white.json"

OUT_IMG = SCRIPT_DIR / "dual_detect_debug.jpg"

# ===============================
# LOAD HSV CONFIGS
# ===============================
def load_hsv(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    return (
        np.array(cfg["lower"]),
        np.array(cfg["upper"]),
        cfg.get("min_area", 300),
    )

tool_min, tool_max, tool_area = load_hsv(TOOL_HSV)
obj_min,  obj_max,  obj_area  = load_hsv(OBJ_HSV)

print("Loaded HSV configs:")
print(" Tool :", TOOL_HSV)
print(" Object:", OBJ_HSV)

# ===============================
# CAMERA
# ===============================
picam2 = Picamera2()
cfg = picam2.create_still_configuration(
    main={"format": "RGB888", "size": (1280, 720)}
)
picam2.configure(cfg)
picam2.start()

frame = picam2.capture_array()
picam2.close()

hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# ===============================
# DETECTION FUNCTION
# ===============================
def detect(mask, min_area):
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < min_area:
        return None

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return (u, v), c

# ===============================
# RUN DETECTION
# ===============================
tool_mask = cv2.inRange(hsv, tool_min, tool_max)
obj_mask  = cv2.inRange(hsv, obj_min,  obj_max)

tool = detect(tool_mask, tool_area)
obj  = detect(obj_mask,  obj_area)

annotated = frame.copy()

if tool:
    (u_t, v_t), c_t = tool
    cv2.drawContours(annotated, [c_t], -1, (0, 255, 0), 2)
    cv2.circle(annotated, (u_t, v_t), 6, (0, 255, 0), -1)
    cv2.putText(
        annotated, "TOOL",
        (u_t + 10, v_t),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
        (0, 255, 0), 2
    )
    print(f"Tool marker @ (u={u_t}, v={v_t})")
else:
    print("Tool marker NOT detected")

if obj:
    (u_o, v_o), c_o = obj
    cv2.drawContours(annotated, [c_o], -1, (0, 0, 255), 2)
    cv2.circle(annotated, (u_o, v_o), 6, (0, 0, 255), -1)
    cv2.putText(
        annotated, "OBJECT",
        (u_o + 10, v_o),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
        (0, 0, 255), 2
    )
    print(f"Chess piece @ (u={u_o}, v={v_o})")
else:
    print("Chess piece NOT detected")

# ===============================
# SAVE DEBUG IMAGE
# ===============================
cv2.imwrite(str(OUT_IMG), annotated)
print(f"Saved debug image: {OUT_IMG}")
