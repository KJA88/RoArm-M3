# Lesson 04 — Vision-Guided Alignment (Authoritative)

## Purpose

This lesson is the **capstone** of the RoArm-M3 lesson series.  
It combines:

- Vision (camera + HSV color detection)
- Calibration (pixel → world mapping via homography)
- Continuous motion control
- Safe, torque-aware operation

The goal is **closed-loop visual servoing**:  
the robot continuously aligns its end effector to a detected object using live camera feedback.

---

## Authoritative Script

### ✅ `tracking_mapped.py`  **(PRIMARY, AUTHORITATIVE)**

This script represents the **final, working solution** for vision-guided alignment.

It implements:

- Continuous tracking loop (not step-based)
- Pixel-space error → world-space correction
- Homography-based mapping from image coordinates to robot XY motion
- Streaming motion commands for smooth convergence
- Torque-safe behavior suitable for extended runtime
- Headless execution (no GUI required)

This file supersedes all earlier alignment attempts.

If you are looking for *the* correct implementation in this lesson, **this is it**.

---

## Calibration Data

### 📐 `data/homography_matrix_clean.npy`

This file contains the calibrated homography matrix used to map camera pixel coordinates
to the robot’s planar workspace.

It is generated through prior calibration steps and is required for accurate alignment.
Do not modify or regenerate unless recalibrating the camera–robot setup.

---

## Archive (Historical / Non-Authoritative)

### 📁 `_archive/`

This folder contains **earlier exploratory attempts** that were necessary to reach the
final solution but are **not authoritative**.

Examples include:

- Step-based alignment approaches
- One-axis correction experiments
- Pixel-follow debug scripts
- Nudge-style controllers
- Table-based tracking experiments

These scripts are preserved **for learning and reference only**.
They should not be used as the primary solution.

The existence of this archive reflects an intentional, iterative engineering process.

---

## Lesson Context

This lesson builds directly on:

- **Lesson 01** — Safe motion and trajectory streaming  
- **Lesson 02** — FK/IK validation and kinematic correctness  
- **Lesson 03** — Vision, HSV calibration, and object detection  

Lesson 04 is where all prior components are integrated into a single,
closed-loop robotic behavior.

---

## Summary

- ✅ `tracking_mapped.py` is the final, working implementation
- 📐 Homography-based mapping enables stable visual servoing
- 🗄 Archived scripts document the development path, not the final solution

This lesson represents the completion of the vision-guided alignment objective.
