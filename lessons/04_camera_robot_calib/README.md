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

Addendum: Execution Notes & Clarifications (Does NOT replace the notes above)

This addendum documents practical details discovered during execution of Lesson 04.
It does not alter the original lesson intent, only clarifies how it was applied.

A. Eye-to-hand vs eye-in-hand (explicit)

Lesson 04 was executed in eye-to-hand configuration:

Camera is fixed in the environment

Robot base frame is fixed

The object is moved

The robot may remain fixed during sampling

This results in datasets where:

(u, v) varies significantly

(x, y, z) may remain constant

This is intentional and valid for learning a camera → robot mapping.

The original lesson text also describes a variant where the robot moves instead.
Both approaches are valid; the eye-to-hand variant was used in practice because it:

simplifies initial mapping

avoids compounding robot motion and vision error

produces a clean first dataset for Lesson 05

B. Why the robot can remain fixed in practice

Although the lesson text mentions moving the robot between samples, Lesson 04 was successfully completed with:

Robot held at a fixed “home” pose

Object moved to multiple positions on the table

This still produces a correct dataset for learning:

(u, v) → object position relative to robot base


Lesson 05 will use offsets from this reference pose, not absolute pose reconstruction.

C. CSV files and Git tracking

The following files are runtime artifacts, not source code:

cam_robot_samples.csv

cam_robot_samples_exploration.csv

debug/

They are intentionally ignored by Git:

Each run produces session-specific data

Calibration data is environment-dependent

Keeping them out of version control prevents confusion and noise

If a reference dataset is ever needed, it should be added explicitly as a labeled example.

D. Debug images (mirroring Lesson 03)

The logger optionally writes debug images on each ENTER press:

Raw frame

HSV mask

Annotated detection with centroid

These images are overwritten each time and exist solely to answer:

Why did detection fail?

Is HSV too strict?

Is lighting or shadow the cause?

They are diagnostic only and not part of the calibration dataset.

E. Sample count guidance (practical vs formal)

The original lesson text mentions 30–50 samples.

In practice:

6–10 well-distributed samples are sufficient for a first demo

More samples improve robustness but are not required initially

Lesson 05 starts with a simple linear mapping, not a full calibration model

The dataset collected during execution used ~9 samples, which is appropriate for rapid progress.

F. Scope boundary (important)

Lesson 04 answers one question only:

Can we reliably log synchronized (u, v) and (x, y, z) pairs without corruption?

It does not:

perform calibration

fit a model

move the robot autonomously

perform grasping

Those behaviors begin in Lesson 05.

End of Addendum