# Lesson 04 – Camera ↔ Robot Sample Logging (u,v → x,y,z)

## Purpose of this lesson

This lesson builds the **data collection bridge** between:

- **Vision (camera pixel space):** (u, v)
- **Robot Cartesian space:** (x, y, z)

The goal is **NOT calibration yet**.

The goal is to reliably collect **paired samples**:

- (u, v) ← camera sees the object  
- (x, y, z) ← robot reports end-effector position  

These samples will be used in **Lesson 05** to learn a camera → robot mapping.

---

## What this lesson actually does

On demand (ENTER key):

1. Capture a frame from the IMX708 camera
2. Detect a colored object using HSV (from Lesson 03)
3. **If the object is detected**:
   - Compute its pixel centroid (u, v)
   - Query the robot firmware for current (x, y, z)
   - Append one row to a CSV file
4. **If the object is NOT visible**:
   - Nothing is logged (this is intentional)

This prevents garbage data.

---

## Files in this lesson

```
lessons/04_camera_robot_calib/
├── cam_robot_log_samples.py
├── cam_robot_samples.csv
├── cam_robot_samples_exploration.csv
├── debug/
└── README.md
```

- **cam_robot_log_samples.py**  
  Main interactive logger (camera + robot feedback)

- **cam_robot_samples.csv**  
  Primary dataset for calibration

- **cam_robot_samples_exploration.csv**  
  Scratch / exploratory data (optional)

- **debug/**  
  Saved raw / mask / annotated images (optional)

---

## Prerequisites (MUST be completed first)

### Lesson 03 must be finished successfully

You must already have:

```
lessons/03_vision_color_detection/hsv_config.json
```

This file defines **what color the camera is looking for**.

If HSV is wrong → detection fails → **no samples are logged**.

---

## Object placement rules (CRITICAL)

For valid samples:

- The object stays **fixed** on the table
- The robot **moves**
- The object must remain **visible** in the camera frame

If the object leaves the frame:

- Detection fails
- (x, y, z) is **NOT recorded**
- This is expected behavior

---

## How to run the logger (TWO-TERMINAL WORKFLOW)

### Terminal 1 — Camera + Logger (leave running)

```
cd ~/RoArm
source .venv/bin/activate
python lessons/04_camera_robot_calib/cam_robot_log_samples.py
```

You will see:

```
=== Lesson 04: Camera → Robot Sample Logger ===
Controls:
  ENTER -> capture (u,v) + (x,y,z)
  q     -> quit
```

Do **not** close this terminal.

---

### Terminal 2 — Robot motion commands

Open a second terminal.

```
cd ~/RoArm
source .venv/bin/activate
```

Move the robot between samples:

```
python roarm_simple_move.py home
python roarm_simple_move.py goto_xyz 230 40 300
python roarm_simple_move.py goto_xyz 210 -40 300
python roarm_simple_move.py goto_xyz 260 0 300
```

After **each** move:

1. Switch back to **Terminal 1**
2. Press **ENTER once**

---

## What a valid sample looks like

Terminal output:

```
[OK #7] u,v=(164,313) x,y,z=(230.79,-18.80,289.69)
```

CSV row:

```
timestamp,u,v,x,y,z
2025-12-13T12:50:58,504,331,59.63,-0.09,551.43
```

Meaning:

- Camera saw object at (u, v)
- Robot reported (x, y, z)
- The pair was saved for calibration

---

## Common confusion points (IMPORTANT)

### Why (x, y, z) sometimes does not change

(x, y, z) only changes **when the robot moves**.

Pressing ENTER multiple times **without moving the arm** logs the same pose.

This is correct behavior.

---

### Why nothing logs when the object is missing

If you see:

```
[NO DETECTION]
```

That means:

- HSV mask found no valid contour
- Object is out of frame **or** HSV is too strict
- **No CSV row is written**

This is a safety feature, not a bug.

---

## Dataset requirement before Lesson 05

Before continuing:

- Object fixed in place
- Robot moved to many poses
- (u, v) changes as (x, y, z) changes
- **30–50 clean samples minimum**

Quick check:

```
head lessons/04_camera_robot_calib/cam_robot_samples.csv
```

You should see variation in **both** camera and robot values.

---

## What Lesson 05 will do

Lesson 05 will:

- Load cam_robot_samples.csv
- Learn a mapping:

```
(u, v) → (x, y, z)
```

- Enable camera-guided robot motion

Lesson 04 exists **only** to make Lesson 05 possible.

---

## Summary (plain English)

- HSV decides what pixels count
- Contours decide what object matters
- (u, v) comes from vision
- (x, y, z) comes from firmware feedback
- We only log data when **both** are valid

You now have a real camera ↔ robot calibration dataset.

This is real robotics work.
