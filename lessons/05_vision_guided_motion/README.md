# Lesson 05 — Autonomous Visual Servoing (Eye-to-Hand)

## Purpose of This Lesson

Lesson 05 is the capstone of the vision sequence.
It converts the paired perception concepts from Lesson 04 into a real-time,
closed-loop autonomous control system.

The goal of this lesson is to enable the robot to:

- Perceive an object’s position in image space (u, v)
- Compute positional error relative to the camera center
- Command smooth, continuous motion to eliminate that error
- Maintain stability and safety during autonomous operation

This lesson represents the transition from observation to action.

---

## What This Lesson Actually Does

Unlike previous lessons, the autonomous script runs continuously and does not
require manual triggering.

The control pipeline consists of:

### 1. Vision Gate (Stability Check)
- Captures frames from a fixed overhead camera
- Requires the object to be detected consistently across multiple frames
- Prevents motion caused by noise, lighting flicker, or false contours

### 2. Error Mapping
- Computes pixel error from the image center (640, 360)
- Maps image-space error to robot-space motion using a calibrated gain
- Uses eye-to-hand geometry (camera does not move with the arm)

### 3. Virtual Pose Tracking
- Maintains an internal “virtual pose” instead of waiting for slow robot feedback
- Enables high-frequency updates (~20 Hz)
- Matches the intended use of the RoArm streaming control interface

### 4. Streaming Control (T:1041)
- Uses non-blocking Cartesian commands
- Sends small incremental updates instead of large jumps
- Produces smooth, continuous motion instead of stepwise movement

### 5. Safety Fencing
- Enforces strict Cartesian limits on every command
- Prevents over-extension, IK instability, and cable strain
- Rejects unstable vision frames before motion is allowed

---

## Files in This Lesson

lessons/05_vision_guided_motion/
├── trackobject_step.py
├── trackobject_auto.py
└── README.md


### trackobject_step.py — Diagnostic Stepwise Servo

- Manual ENTER-triggered visual servo
- Used to verify:
  - Correct axis mapping
  - Correct motion direction
  - Safe inverse-kinematics behavior
- Intentionally conservative and human-gated
- Must be run first before autonomous operation

### trackobject_auto.py — Autonomous Visual Tracking (Capstone)

- Fully autonomous visual servoing
- Streams motion at ~20 Hz using T:1041
- Implements:
  - Vision stability checks
  - Per-cycle motion clipping
  - Cartesian safety fencing
- This is the final Lesson 05 deliverable

---

## Technical Discoveries & Solutions

### 1. The “IK Slam” Problem

**Issue:**
Large Cartesian jumps (> ~15 mm) caused violent elbow flips and unsafe motion.

**Solution:**
All per-cycle motion is clipped to small increments, ensuring the IK solver
remains in a locally solvable region at all times.

---

### 2. Protocol Optimization

**Issue:**
Blocking Cartesian commands (T:104) caused jerky, stop-start behavior.

**Solution:**
Switched to streaming non-blocking control (T:1041), allowing continuous
trajectory updates synchronized with the camera.

---

### 3. Lighting & Perception Sensitivity

**Issue:**
Single bad vision frames could trigger unsafe motion.

**Solution:**
Added a multi-frame stability requirement. The robot only moves when object
detection is consistent across consecutive frames.

---

## Safety Boundaries (The Fence)

To protect hardware and wiring, all commands are constrained to:

- X (Reach): 200 mm → 380 mm
- Y (Rotation): −150 mm → +150 mm
- Z (Height): Fixed at 260 mm (safe elbow clearance)

Commands outside this region are clipped automatically.

---

## How to Run

### Manual Verification (Required First)

```bash
python3 trackobject_step.py

    Move the object by hand

    Verify the robot moves in the correct direction

    Confirm no joint stress or unexpected motion

Autonomous Tracking

python3 trackobject_auto.py

    The robot tracks the object continuously

    Motion stops automatically when the object is centered

    Motion is gated off if vision becomes unstable

Important: Always command the robot to a known safe pose before rebooting.
Lesson Outcome

At the completion of Lesson 05, the system demonstrates:

    Eye-to-hand visual servoing

    Continuous streaming Cartesian control

    Practical IK-aware motion behavior

    Real-world safety constraints

This lesson intentionally avoids camera calibration or depth modeling.
Those topics are introduced in Lesson 06.
