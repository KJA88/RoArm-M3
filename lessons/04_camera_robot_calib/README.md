Lesson 04 – Camera ↔ Robot Sample Logging (u,v → x,y,z)
Purpose of this lesson

This lesson builds the data collection bridge between:

Vision (camera pixel space) → (u, v)

Robot Cartesian space → (x, y, z)

The goal is not calibration yet.

The goal is to reliably collect paired samples:

(u, v)  ← camera sees object
(x, y, z) ← robot reports end-effector position


These samples will be used in Lesson 05 to learn a camera→robot mapping.

What this lesson actually does

On demand (ENTER key):

Capture a frame from the IMX708 camera

Detect a colored object using HSV (from Lesson 03)

If the object is detected:

Compute its pixel centroid (u, v)

Query the robot firmware for current (x, y, z)

Append one row to a CSV file

If the object is not visible:

Nothing is logged (this is intentional)

This prevents garbage data.

Files in this lesson
lessons/04_camera_robot_calib/
├── cam_robot_log_samples.py      # Main interactive logger
├── cam_robot_samples.csv         # Primary dataset
├── cam_robot_samples_exploration.csv  # Scratch / exploratory data
├── debug/                        # Saved debug images (optional)
└── README.md

Prerequisites (must be done first)
1. Lesson 03 completed successfully

You must already have:

lessons/03_vision_color_detection/hsv_config.json


This file defines what color the camera is looking for.

If HSV is wrong → detection fails → no samples logged.

2. Object placement rules (CRITICAL)

For valid samples:

The object stays fixed on the table

The robot moves

The object must remain visible in the camera frame

If the object leaves the frame:

Detection fails

(x,y,z) is NOT recorded

This is expected behavior

How to run the logger (correct workflow)
Terminal 1 – Camera + Logger (leave running)
cd ~/RoArm
source .venv/bin/activate
python lessons/04_camera_robot_calib/cam_robot_log_samples.py


You will see:

=== Lesson 04: Camera → Robot Sample Logger ===
Controls:
  ENTER  -> capture (u,v) + (x,y,z)
  q      -> quit


Do not close this terminal.

Terminal 2 – Robot motion commands

Use this terminal to move the arm between samples:

cd ~/RoArm
source .venv/bin/activate


Examples:

python roarm_simple_move.py home
python roarm_simple_move.py goto_xyz 230 40 300
python roarm_simple_move.py goto_xyz 210 -40 300
python roarm_simple_move.py goto_xyz 260 0 300


After each move:

Go back to Terminal 1

Press ENTER once to log a sample

What a valid sample looks like

Terminal output:

[OK #7] u,v=(164,313) x,y,z=(230.79,-18.80,289.69)


CSV row:

timestamp,u,v,x,y,z
2025-12-13T12:50:58,504,331,59.63,-0.09,551.43


This means:

The camera saw the object at pixel (u,v)

The robot reported its actual pose (x,y,z)

The pair is now saved for calibration

Why (x,y,z) sometimes did not change

This caused confusion and is important:

(x,y,z) only changes when the robot actually moves

Pressing ENTER repeatedly without moving the arm logs the same pose

This is expected and correct behavior

To build a useful dataset:

Move the robot

Then press ENTER once

Why nothing logs when the object is missing

If you see:

[NO DETECTION]


That means:

The HSV mask found no valid contour

The object is out of frame or HSV is too strict

No CSV row is written

This is a safety feature, not a bug.

Dataset requirement before Lesson 05

Before proceeding, you need:

Object fixed in place

Robot moved to many different poses

(u,v) changing as (x,y,z) changes

At least 30–50 clean samples

You can verify quickly:

head lessons/04_camera_robot_calib/cam_robot_samples.csv


You should see variation in both (u,v) and (x,y,z).

What Lesson 05 will do

Lesson 05 will:

Load cam_robot_samples.csv

Learn a mapping:

(u, v) → (x, y, z)


Enable camera-guided robot motion

Lesson 04 exists only to make Lesson 05 possible.

Summary (plain English)

HSV decides what pixels count

Contours decide what object matters

(u,v) comes from vision

(x,y,z) comes from firmware feedback

We only log data when both are valid

You now have a real calibration dataset

This is real robotics work.

Next step

Once you confirm your CSV looks good:

➡️ Proceed to Lesson 05 – Camera → Robot Calibration

Now: how to add this README to GitHub

From repo root:

nano lessons/04_camera_robot_calib/README.md


Paste everything above → save → exit.

Then:

git add lessons/04_camera_robot_calib/README.md
git commit -m "Lesson 04 README: camera-robot sample logging workflow"
git push origin main
