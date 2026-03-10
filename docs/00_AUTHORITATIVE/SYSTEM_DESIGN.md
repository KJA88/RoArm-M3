# RoArm-M3-S — Full System Design Specification

## Document Authority

This document defines the authoritative system design and milestone progression
for the RoArm-M3-S project.

Only work completed and demonstrated under the `/milestones` directory is
considered **current and authoritative**.

Lessons, experiments, and archived code may inform milestones, but **do not
define system capability on their own**.

---

## Phase 1: System Authority (The Foundation)

This phase is about **Trust**.  
The system does not accept task-space commands until joint authority and
deterministic command–response behavior are proven.

**Invariant:**  
The system never accepts task-space commands unless joint authority and a
deterministic handshake have been verified.

---

### Milestone 00: Safety Contract

**Implementation:**  
Establish a torque-safe boot and shutdown state.

**Goal:**  
Ensure the arm defaults to a zero-energy condition to prevent accidental motion
or collisions.

---

### Milestone 01: Joint Authority

**Implementation:**  
SDK-mediated joint control via the Supervisor layer.

**Goal:**  
Prove a 1-to-1 mapping between commanded joint radians and physical joint motion.

**Authority Rules:**
- Joint motion is issued via SDK interfaces only
- Raw UART usage is forbidden
- A known-good reference pose (“Home”) is established and recoverable

---

### Milestone 02: Mechanical Truths

**Implementation:**  
Software interlocks and limits (e.g. 1.1 rad gripper hard stop).

**Goal:**  
Prevent hardware damage by encoding physical constraints directly into software.

---

### Milestone 03: Deterministic Pipelines

**Implementation:**  
SDK-based command handshaking and response validation.

**Goal:**  
Guarantee deterministic behavior under the rule:

> **One Command → One Response**

**Requirements:**
- Read state before motion
- Issue exactly one command
- Read state after motion
- Log all actions
- Disengage torque on exit

---

## Phase 2: Task-Space Authority (Motion Logic)

This phase establishes **Cartesian control authority** for the RoArm-M3 using the
arm’s **internal firmware inverse kinematics (IK) solver**.

No inverse kinematics math is implemented in this phase.
The firmware solver is treated as a **black box** and validated empirically using
SDK-approved interfaces.

---

### Milestone 04: Task-Space Framing & Assumptions

**Purpose:**  
Establish an unambiguous definition of task-space commands before execution.

**Defines:**
- The task-space coordinate frame used by the SDK
- The meaning of X, Y, Z, and Pitch for the RoArm-M3
- Workspace assumptions and safety boundaries
- What constitutes a valid pose request

**Explicitly Out of Scope:**
- Inverse kinematics math
- Solver implementation details
- Planar or reduced-dimension assumptions

This milestone prevents semantic and frame-of-reference errors in all subsequent
task-space control.

---

### Milestone 05: Firmware IK Validation (Protocol Characterization)

Purpose:
Empirically characterize the RoArm-M3 internal firmware IK solver by issuing
absolute task-space pose commands via the SDK and observing real hardware
behavior.

Protocol Scope:

Task-space motion is attempted using the SDK pose_ctrl() interface

The underlying UART protocol is observed and recorded, not assumed

Any required initialization or alternate opcode behavior is treated as
empirical data

Validation Method:

Define a bounded 3D “Safe Box” workspace

Command poses using pose_ctrl() (or equivalent raw protocol)

Query pose feedback after motion

Measure and log positional error

Record unreachable, clamped, or ignored targets

Explicitly Out of Scope:

Custom inverse kinematics

Planar math models

Solver enforcement or correction

Assumptions about firmware correctness

Outcome:
This milestone establishes measured, documented task-space behavior of the
firmware IK solver, including protocol requirements and failure modes.

---

### Milestone 06: Trajectory Streaming

**Purpose:**  
Demonstrate continuous, smooth motion under task-space control.

**Method:**
- Generate interpolated task-space paths (line, circle)
- Stream sequential `pose_ctrl()` commands
- Maintain constant timing between commands

**Goal:**  
Prove deterministic trajectory execution rather than discrete pose teleportation.

---

## Phase 3: Kinematics & Mathematical Authority

This phase audits and challenges the firmware’s internal kinematics.

It is not required to make the robot move.
It exists to prove understanding beyond black-box usage.

---

### Milestone 07: Coordinate Frames

**Implementation:**  
Base-link vs Tool-Center-Point (TCP) modeling.

**Goal:**  
Ensure spatial reasoning remains correct regardless of arm configuration.

---

### Milestone 08: Denavit–Hartenberg (DH) Parameters

**Implementation:**  
Formal DH parameterization of the arm.

**Goal:**  
Enable professional-grade kinematic modeling and prediction.

---

### Milestone 09: Custom vs Firmware IK

**Implementation:**  
Compare an external IK solver (e.g. IKFast) against firmware IK.

**Procedure:**
1. Compute joint angles using custom IK
2. Command joints via SDK-mediated joint control
3. Query pose feedback
4. Compare expected vs actual pose

**Goal:**  
Demonstrate independent kinematic reasoning and model validation.

---

## Phase 4: Perception (The Robot’s Eyes)

This phase integrates vision into the system.

**Rule:**  
Vision never commands joints directly.  
Vision supplies task-space targets only.

---

### Milestone 10: Camera Calibration

**Implementation:**  
Intrinsic calibration and color/feature filtering.

**Goal:**  
Remove distortion and enable reliable feature detection.

---

### Milestone 11: Pixel-to-World Mapping

**Implementation:**  
Homography and coordinate transformations.

**Goal:**  
Convert pixel coordinates into task-space coordinates.

---

### Milestone 12: Vision-Guided Alignment

**Implementation:**  
Closed-loop visual servoing.

**Goal:**  
Automatically align the end-effector with detected targets.

---

## Phase 5: Sensor Fusion & Autonomy

This phase enables robust operation under real-world uncertainty.

---

### Milestone 13: Distance Awareness (ToF)

**Implementation:**  
Integrate time-of-flight distance sensing.

**Goal:**  
Measure distance prior to interaction.

---

### Milestone 14: Force Sensing (FSR)

**Implementation:**  
Gripper force/pressure sensing.

**Goal:**  
Enable soft-touch grasping.

---

### Milestone 15: Sensor Fusion

**Implementation:**  
Fuse vision, distance, and force data.

**Goal:**  
Enable multi-sensory decision making.

---

### Milestone 16: State Machines

**Implementation:**  
Formal state-machine control logic.

**Goal:**  
Enable recovery from environmental or execution changes.

---

### Milestone 17: Complex Task Planning

**Implementation:**  
Autonomous pick-and-place and sequencing logic.

**Goal:**  
Demonstrate a complete automated work cell.

---

### Milestone 18: Failure Recovery

**Implementation:**  
Exception handling and safe-failure states.

**Goal:**  
Ensure failures do not damage hardware or endanger humans.
