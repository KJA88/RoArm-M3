# Lesson 06 — Geometry-Aware Visual Alignment (Eye-to-Hand)

## Purpose of This Lesson

Lesson 06 advances the system from **continuous visual tracking**
(Lesson 05) to **deterministic geometric alignment** suitable for
physical interaction (pick, place, grasp).

The key shift in this lesson is moving from:

> “continuously chase the object”  
to  
> “align deliberately, then stop”

This lesson focuses on **stability, intentional stopping, and control
discipline**, not speed or complexity.

---

## Conceptual Shift from Lesson 05

### Lesson 05
- Continuous closed-loop visual servoing
- Robot is always correcting error
- Motion never intentionally “finishes”
- Best for tracking and following

### Lesson 06
- Discrete motion phases
- Explicit alignment → hold → action
- Robot **intentionally stops moving**
- Best for manipulation and task execution

Lesson 06 is the bridge between vision and manipulation.

---

## What This Lesson Actually Does

Lesson 06 implements **base-yaw visual alignment** using a fixed camera
(eye-to-hand configuration):

- The robot rotates its **base joint only**
- The end-effector Z height is held constant
- Alignment is determined using **image geometry**, not calibration
- Motion stops automatically once alignment is achieved

No inverse kinematics solving is performed inside the control loop.
Only safe, bounded joint motion is used.

---

## Control Strategy Overview

### 1. Fixed Geometry Assumptions

- Camera is fixed in the environment
- Robot base frame is fixed
- Object moves in the workspace
- Z height is known and safe

This simplifies the control problem and reduces failure modes.

---

### 2. Image-Space Error Measurement

- Object centroid is detected in image space `(u, v)`
- Horizontal pixel error `du = u − center_x` is used
- Vertical error is observed but not directly actuated

The robot does **not** attempt to estimate depth in this lesson.

---

### 3. Base Yaw Control Only

- Only joint 1 (base yaw) is commanded
- Small incremental angle updates are sent
- Motion is clipped to safe angular limits

This avoids elbow flips, IK singularities, and cable stress.

---

### 4. Early-Stop Geometry (Key Insight)

Rather than relying only on pixel tolerance, the system detects when:

- Horizontal error magnitude begins decreasing
- Vertical error magnitude begins increasing

This indicates the robot has **passed the object’s projection** in the
camera frame.

At this point:
- Motion is stopped immediately
- The base joint is locked
- No further commands are sent

This produces a clean, repeatable stop without oscillation.

---

### 5. Hold State

Once alignment is achieved:

- The robot enters a “hold” state
- No corrective motion is attempted
- The system is ready for the next phase (e.g., descent or grasp)

This is critical for manipulation tasks.

---

## Torque-Safe Behavior

- Torque is enabled explicitly at startup
- Torque is **never dropped automatically**
- Both `q` and `Ctrl+C` exit cleanly
- The robot holds position on exit

This prevents sudden collapses and protects hardware.

---

## Files in This Lesson

lessons/06_transform_and_depth/
├── pick_and_place_hybrid.py
├── _archive/
└── README.md

yaml
Copy code

### pick_and_place_hybrid.py — Active Script

This is the **only active runtime file** for Lesson 06.

It implements:
- Base yaw visual alignment
- Early-stop detection
- Motion hold state
- Headless operation
- Torque-safe exit handling

---

### _archive/

Contains legacy and exploratory files, including:
- Calibration experiments
- Earlier pick-and-place attempts
- Data artifacts

These files are preserved for reference but are **not executed**.

---

## Why Calibration Is Not Used Here

Although calibration artifacts exist, Lesson 06 demonstrates that:

- Reliable alignment can be achieved without full world calibration
- Image-space geometry is sufficient for yaw alignment
- Calibration adds complexity without benefit for this task

Full `(u, v) → (x, y, z)` calibration is a **future extension**, not a
requirement for stable interaction.

---

## How to Run

```bash
python3 pick_and_place_hybrid.py
Place the target object on the table

The robot will rotate its base to align with the object

Motion stops automatically once alignment is achieved

Press q or Ctrl+C to exit safely

Lesson Outcome
At the completion of Lesson 06, the system demonstrates:

Deterministic visual alignment

Intentional motion stopping

Stable torque-safe behavior

Clean separation between tracking and action

This lesson prepares the system for:

Grasping

Pick-and-place

Task-level sequencing

Higher-level autonomy
