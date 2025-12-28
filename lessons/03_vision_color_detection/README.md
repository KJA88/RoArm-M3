# Lesson 03 – Vision: Color-Based Object Detection (FINAL)

This lesson provides a clean, reusable vision module for detecting colored objects
in camera pixel space using HSV thresholding.

## Scope (Important)

Lesson 03 answers **one question only**:

> Can the camera reliably detect one or more colored objects and return their pixel
> centroids `(u, v)`?

This lesson does **not**:
- Move the robot
- Perform IK or FK
- Map pixels to world coordinates
- Perform calibration math

Those steps happen in later lessons.

---

## Files Overview

### Core Tools (Authoritative)

- `quick_hsv_calibrate.py`  
  Single-step HSV calibration tool. Captures one frame, samples the image center,
  and writes an HSV config.

- `camera_dual_color_test.py`  
  Vision-only test that loads multiple HSV configs and prints detected centroids.

- `hsv_utils.py`  
  Shared helper for loading HSV configs.

### Data

- `hsv/default.json`  
  Canonical single-object HSV configuration.

- `hsv/chess_white.json`  
  Explicit HSV config for white chess pieces.

- `hsv/tool_marker.json`  
  HSV config for the tool-mounted visual marker.

---

## Workflow

### 1. Calibrate an object (single command)

Place the object at the **center of the camera view**, then run:

```bash
python3 quick_hsv_calibrate.py
This writes to:

pgsql
Copy code
hsv/default.json
To create an explicit named config:

bash
Copy code
python3 quick_hsv_calibrate.py chess_white.json
python3 quick_hsv_calibrate.py tool_marker.json
Each run also saves:

mipsasm
Copy code
frame_with_square.jpg
for visual confirmation.

2. Validate detection (no robot involved)
bash
Copy code
python3 camera_dual_color_test.py
This prints detected centroids:

yaml
Copy code
Chess: (u, v) | Tool: (u, v)
Move objects independently to confirm stable detection.

Deprecated Files
Older learning scripts have been archived in _deprecated/ and are no longer used.
They are kept only for reference.

Freeze Rule
Lesson 03 is frozen after this point.

Future lessons import vision utilities from here but do not modify this lesson.