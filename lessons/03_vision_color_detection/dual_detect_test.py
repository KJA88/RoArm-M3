#!/usr/bin/env python3
"""
Dual HSV Detection Test (Vision Only)

- Prompts user to select HSV profiles from profiles/
- Captures ONE frame
- Detects selected objects
- Prints (u, v) for each
- Saves annotated image as dual_detect_image.jpg

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
HSV_DIR = SCRIPT_DIR / "profiles"
OUT_IMG = SCRIPT_DIR / "dual_detect_image.jpg"

# ===============================
# PROFILE SELECTION
# ===============================
def choose_profile(label):
    profiles = sorted(p.name for p in HSV_DIR.glob("*.json"))

    if not profiles:
        print("No HSV profiles found in profiles/. Run calibrate_hsv.py first.")
        exit(1)

    print("\nAvailable HSV profiles:")
    for i, name in enumerate(profiles):
        print(f"  [{i}] {name}")

    while True:
        choice = input(f"Select {label} profile (index or ENTER to skip): ").strip()
        if choice == "":
            return None
        if choice.isdigit() and int(choice) < len(profiles):
            return HSV_DIR / profiles[int(choice)]
        print("Invalid selection. Try again.")

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

TOOL_HSV = choose_profile("TOOL")
OBJ_HSV  = choose_profile("OBJECT")

tool_cfg = load_hsv(TOOL_HSV) if TOOL_HSV else None
obj_cfg  = load_hsv(OBJ_HSV)  if OBJ_HSV else None

print("\nLoaded HSV configs:")
print(" Tool :", TOOL_HSV if TOOL_HSV else "None")
print(" Object:", OBJ_HSV if OBJ_HSV else "None")

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
annotated = frame.copy()

if tool_cfg:
    tool_min, tool_max, tool_area = tool_cfg
    tool_mask = cv2.inRange(hsv, tool_min, tool_max)
    tool = detect(tool_mask, tool_area)

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

if obj_cfg:
    obj_min, obj_max, obj_area = obj_cfg
    obj_mask = cv2.inRange(hsv, obj_min, obj_max)
    obj = detect(obj_mask, obj_area)

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
        print(f"Object @ (u={u_o}, v={v_o})")
    else:
        print("Object NOT detected")

# ===============================
# SAVE DEBUG IMAGE
# ===============================
cv2.imwrite(str(OUT_IMG), annotated)
print(f"Saved debug image: {OUT_IMG}")
