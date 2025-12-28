# Lesson 05 — Autonomous Visual Servoing (Eye-to-Hand)

## Purpose of This Lesson

Lesson 05 is the capstone of the vision sequence.
It converts perception from Lesson 04 into a real-time, closed-loop
autonomous control system using a fixed (eye-to-hand) camera.

The goal of this lesson is to enable the robot to:

- Perceive an object’s position in image space (u, v)
- Compute positional error relative to the camera center
- Command smooth, continuous Cartesian motion to reduce that error
- Maintain stability and safety during autonomous operation

This lesson represents the transition from **observation** to **action**.

---

## What This Lesson Actually Does

Lesson 05 implements **image-space visual servoing**.
The robot does not reason about world coordinates or depth.
Instead, it continuously adjusts its pose to minimize pixel error.

The control loop runs continuously and does not require manual triggering
in autonomous mode.

---

## Control Pipeline

### 1. Vision Detection

- Captures frames from a fixed overhead camera
- Detects the target object using HSV color segmentation
- Computes the object centroid in image space (u, v)

---

### 2. Image-Space Error Computation

- Computes pixel error relative to the camera center (640, 360)
- Error is defined as:
  - `du = u - 640`
  - `dv = v - 360`

No calibration or depth estimation is performed in this lesson.

---

### 3. Virtual Pose Tracking

- Maintains an internal **virtual Cartesian pose**
- Avoids waiting on slow serial feedback each cycle
- Enables higher control rates (~20–30 Hz)

This matches the intended use of the RoArm streaming interface.

---

### 4. Streaming Cartesian Control (T:1041)

- Uses non-blocking Cartesian streaming commands
- Sends small incremental pose updates
- Produces smooth, continuous motion instead of stepwise jumps

Large jumps are intentionally avoided to keep the IK solver in a stable region.

---

### 5. Safety Fencing

Every command is clipped to a predefined safe workspace:

- Prevents over-extension
- Prevents IK instability
- Protects cables and joints

Safety fencing is enforced **every cycle**, not just at startup.

---

## Files in This Lesson

lessons/05_vision_guided_motion/
├── trackobject_step.py
├── trackobject_auto.py
└── README.md

yaml
Copy code

---

### trackobject_step.py — Diagnostic Stepwise Servo

- Manual ENTER-triggered visual servo
- Designed for debugging and verification
- Used to confirm:
  - Correct axis mapping
  - Correct motion direction
  - Safe IK behavior
- Motion is slow, gated, and human-controlled

**This script should always be run first.**

---

### trackobject_auto.py — Autonomous Visual Tracking (Capstone)

- Fully autonomous visual servoing
- Streams Cartesian motion continuously
- Implements:
  - Per-cycle motion clipping
  - Cartesian safety fencing
  - Torque-safe shutdown behavior
- Represents the final Lesson 05 deliverable

---

## Key Technical Discoveries

### 1. The “IK Slam” Problem

**Issue:**  
Large Cartesian jumps caused violent elbow flips and unsafe motion.

**Solution:**  
Per-cycle motion is strictly clipped to small increments, keeping the IK
solver in a locally stable region at all times.

---

### 2. Streaming vs Blocking Commands

**Issue:**  
Blocking Cartesian commands caused jerky, stop-start motion.

**Solution:**  
Switched to non-blocking streaming control (T:1041), enabling smooth,
camera-synchronized updates.

---

### 3. Vision Noise Sensitivity

**Issue:**  
Single bad vision frames could trigger incorrect motion.

**Solution:**  
Motion is gated and limited per cycle. Instability results in reduced or
halted motion rather than unsafe jumps.

---

## Safety Boundaries

All autonomous motion is constrained to:

- X (Reach): 200 mm → 380 mm
- Y (Lateral): −150 mm → +150 mm
- Z (Height): Fixed at 260 mm

Commands outside this region are clipped automatically.

---

## How to Run

### Manual Verification (Required)

```bash
python3 trackobject_step.py
Move the object by hand

Verify correct motion direction

Confirm safe behavior

Autonomous Tracking
bash
Copy code
python3 trackobject_auto.py
Robot tracks the object continuously

Motion stops when the object is centered

Torque remains enabled on exit

Lesson Outcome
At the completion of Lesson 05, the system demonstrates:

Eye-to-hand visual servoing

Continuous streaming Cartesian control

IK-aware motion behavior

Practical safety constraints

This lesson intentionally avoids calibration and depth modeling.
Those concepts are introduced in Lesson 06.