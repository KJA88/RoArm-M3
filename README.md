# RoArm-M3-S / RoArm-M3-Pro – Python Control & Kinematics

This repo is my **Python control stack and kinematics lab** for the Waveshare RoArm-M3-S / RoArm-M3-Pro arm.

It is meant to be:

- A **clean, documented control stack** (Python → UART → JSON → robot)
- A **validated kinematics + calibration model** (shoulder-origin planar FK/IK)
- A **safe base** for future work: trajectories, vision, IK pick-and-place
- A **portfolio-quality robotics project** another engineer (or AI) can continue.

---

## TL;DR – How to Drive the Arm

From the repo root on the Pi:

    cd ~/RoArm

    # (optional) activate your venv
    source ~/.venv/bin/activate

    # Home to tall “candle” pose
    python3 roarm_simple_move.py home

    # Move to a canonical test point (X=235, Y=0, Z=234)
    python3 roarm_simple_move.py goto_xyz 235 0 234

    # Print firmware XYZ + joints
    python3 roarm_simple_move.py feedback

- Typical serial device: `/dev/ttyUSB0`  
- Stable ID: `/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_…`

---

## What This Repo Actually Does

### 1. Simple, Safe Runtime Control (Core Script)

`roarm_simple_move.py` – main daily-use script.

Supported subcommands:

- `home` → go to tall “candle” pose  
- `feedback` → print firmware XYZ + joint angles  
- `goto_xyz X Y Z` → move to XYZ using **calibrated planar IK**

Examples:

    python3 roarm_simple_move.py home
    python3 roarm_simple_move.py goto_xyz 235 0 234
    python3 roarm_simple_move.py feedback

Under the hood it uses:

- `T=105` – firmware feedback (XYZ + joints)  
- `T=102` – full joint control in radians  
- A **shoulder-origin 2-link planar model + base yaw** with parameters from `planar_calib.json`.

---

### 2. Calibration & Kinematics Tools

These live in the repo root because they’re part of the core stack:

- `roarm_collect_samples_safe.py`  
  Safely collects real-world samples of  
  (shoulder, elbow) → (x, z) from the arm.

- `roarm_fit_planar.py`  
  Fits the planar model parameters:

  - `L1`, `L2` – link lengths  
  - `X0`, `Z0` – Cartesian offsets  
  - `shoulder_offset`, `elbow_offset` – joint zero offsets  

  Writes them into `planar_calib.json` via least squares.

  ⚠️ `planar_calib.json` must **only** be rewritten by `roarm_fit_planar.py`.  
  Do **not** hand-edit this file.

- Historical calibration file:

  - `roarm_arm_characterization_CALIBRATED.json`  
    Old DH-based characterization, kept for history.

---

### 3. Runtime Planar Model (FK/IK)

The runtime FK/IK is fully documented in:

- `docs/runtime_planar_model.md`  
- `docs/fk_*.md`, `docs/ik_*.md` (hand calculations)

Effective joint angles:

- `φ    = shoulder + shoulder_offset`  
- `e_eff = elbow + elbow_offset`  
- `φ₂   = φ + e_eff`

Planar FK (shoulder-origin):

- `x_p = L1·sin(φ) + L2·sin(φ₂) + X0`  
- `z_p = L1·cos(φ) + L2·cos(φ₂) + Z0`

Base rotation:

- `x = cos(base) · x_p`  
- `y = sin(base) · x_p`  
- `z = z_p`

Planar IK (used by `goto_xyz`):

1. `base = atan2(y, x)`  
2. `x_p = hypot(x, y)`  
3. Subtract offsets: `x_s = x_p – X0`, `z_s = z – Z0`  
4. Solve triangle with law-of-cosines → `e_eff`  
5. Solve for `φ` from geometry  
6. Back out joint angles:

   - `shoulder = φ    – shoulder_offset`  
   - `elbow    = e_eff – elbow_offset`

This is the same math used in both docs and code.

---

## Lessons & Demos (Everything Under `lessons/`)

To keep the root clean, all **learning/demo scripts** are grouped under `lessons/`.  
These are not required for basic use, but they show off skills for hiring / portfolio.

---

### `lessons/01_trajectory_and_gripper/`

Trajectory control + gripper tools.

- `circle_demo.py`  
  - Uses firmware IK (`T=104` / `T=1041`)  
  - Streams circle / helix trajectories in task space  
  - Demonstrates joint-space streaming at ~25 Hz over UART.

  Run from repo root:

      python3 lessons/01_trajectory_and_gripper/circle_demo.py

- `gripper_sweep.py`, `roarm_gripper.py`, `roarm_safety.py`  
  - Gripper angle sweep and helper  
  - Encodes safe gripper range and basic joint safety checks.

---

### `lessons/02_kinematics_fk_ik/`

Kinematics validation (no robot movement).

- `test_fk_ik_consistency.py`  
  - Randomly samples reachable (x, z) points  
  - Runs IK → FK → checks position error  
  - Prints mean/max error and counts IK failures

  Example run:

      python3 lessons/02_kinematics_fk_ik/test_fk_ik_consistency.py

  Typical result (current calibration):

  - ~300 samples  
  - ~0.4 mm mean & max error  
  - ~0 IK failures in the main workspace  

This script is the harness that proves the planar FK/IK + calibration are numerically sound.

---

### `lessons/03_vision_color_detection/`

Camera + color-based object detection using the IMX708 (Camera Module 3 / Arducam variant).

Key scripts:

- `camera_snap.py`  
  - Grabs a single frame using Picamera2  
  - Writes `frame.jpg` to disk

- `inspect_center_hsv.py`  
  - Loads `frame.jpg`  
  - Takes a small patch in the center of the image  
  - Prints average H/S/V → used to learn what color the object looks like to the camera

- `detect_object_from_frame.py`  
  - Uses a chosen HSV range to:
    - Build a mask  
    - Find the largest blob of that color  
    - Draw a red dot at the centroid and green contour  
    - Save `frame_annotated.jpg`

- `camera_color_localize_picam2.py`  
  - Live version: grabs a frame directly from Picamera2  
  - Applies the HSV rule  
  - Outputs `(u, v)` pixel coordinates of the object center  
  - Saves an annotated JPEG with:
    - Red centroid dot  
    - Green outline  
    - Blue image center crosshair

- `cam_robot_sample_once.py`  
  - Combines camera + robot:
    - Gets `(u, v)` from the camera  
    - Queries firmware with `T=105` → `T=1051` feedback  
    - Prints a sample pair: `(u, v, x, y, z)`

These are the first building blocks for camera → robot calibration and future pick-and-place.

---

## Command Cheatsheet

See: `docs/command_cheatsheet.md`

Includes:

- `home`, `goto_xyz`, `feedback` usage  
- Torque off/on scripts:

    python3 torque_off.py
    python3 torque_on.py

- Raw JSON examples using `serial_simple_ctrl.py`  
- Venv activation/deactivation commands  
- USB device reminders

---

## Engineering Log & History

Long-term technical memory is captured in:

- `docs/history_issues_and_fixes.md`  
  - Early mistakes (wrong origin, JSON keys, etc.)  
  - How they were found and fixed

- `docs/roarm_kinematics_control_log.json`  
  - Coordinate frame rules  
  - Joint sign conventions  
  - Calibration values  
  - Canonical test target  
  - Guardrails to avoid regressions

This is so future work (yours or someone else’s) does **not** repeat old bugs.

---

## Repository Layout (High Level)

Core files in repo root:

- `README.md` – this file  
- `LICENSE` – MIT  
- `requirements.txt` – Python dependencies  
- `planar_calib.json` – current planar calibration (fitted, do not edit by hand)  
- `calibrated_dh.json` – DH parameters (historical)  
- `roarm_arm_characterization_CALIBRATED.json` – original characterization data  

Core scripts:

- `roarm_simple_move.py`  
- `roarm_collect_samples_safe.py`  
- `roarm_fit_planar.py`  
- `serial_simple_ctrl.py`  
- `torque_off.py`, `torque_on.py`

Support directories:

- `docs/` – math derivations, logs, cheatsheet, runtime model docs  
- `archive/` – old/unused scripts kept for safety  
- `lessons/` – organized learning/demo code (trajectory, kinematics tests, vision, etc.)

---

## Safety Notes

- Prefer `z ≥ 150 mm` for normal motion; go lower only in controlled tests.  
- Gripper:
  - `g < 1.1 rad` risks stalling the gripper servo  
  - Typical working range: ≈1.2 rad (wide) → ≈3.2 rad (fully closed)
- Always home before new IK experiments.  
- Keep USB slack and watch cables while rotating the base.  
- Respect shoulder/elbow mechanical limits and avoid hard-stopping joints.

---

## Purpose (for Hiring / Future Work)

This repo demonstrates:

- Real robot control via Python → UART → JSON  
- A documented and validated planar kinematics model  
- A repeatable calibration pipeline  
- A clean repo structure (`docs/`, `lessons/`, `archive/`, core scripts at root)  
- A path forward to:
  - Joint-space trajectories  
  - Camera-based detection  
  - Camera → robot calibration  
  - IK-driven pick-and-place  

The intent is that another engineer—or another AI—can open this repo and **safely continue from here** without rediscovering all the hard parts.
::contentReference[oaicite:0]{index=0}
