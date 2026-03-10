Milestone 07 — Coordinate Frames

Phase: 3 — Geometry & Rigor
Status: IN PROGRESS → LOCKABLE

Primary Question Answered

Can the software correctly reason about multiple coordinate frames along the kinematic chain and transform between them without relying on firmware shortcuts?

This milestone proves spatial reasoning, not motion capability.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 05 — Empirical firmware IK behavior

Milestone 06 — Continuous task-space motion

Produces Guarantees For

Milestone 08 — DH parameterization

Milestone 09 — Custom vs firmware IK comparison

Phase 4 — Vision-to-world mapping

Explicitly NOT Responsible For

Moving the robot

Streaming trajectories

IK solving

Motion planning

Vision calibration

Error correction

DO NOT

Call firmware IK

Use pose_ctrl for validation

“Eyeball” correctness

Hardcode world assumptions

Mix perception with geometry

Violating any of the above invalidates Milestone 07.

Intent

Up to Milestone 06, the system treated the arm as if XYZ described the hand.

That is a useful lie.

Milestone 07 removes that lie.

This milestone establishes that:

The robot is a chain of rigid transforms

Coordinates exist in multiple frames

The gripper tip (TCP) is not the wrist joint

Software can reason about these frames explicitly

No motion is required to prove this.

Frames Defined in This Milestone
1. Base Frame ({B})

Origin at the center of the robot base

Fixed in the world

Used as the reference frame for all reasoning

2. Wrist Frame ({W})

Located at the final revolute joint

Rotates with joint configuration

This is where firmware task-space often pretends the tool ends

3. Tool Center Point — TCP ({T})

Located at the actual interaction point (gripper tip)

Offset from {W} by a fixed tool vector

Depends on wrist orientation

This milestone establishes the transform:

{B} → {W} → {T}

Tool Offset Model
Assumed Tool Offset

For this milestone, the tool is modeled as:

Length: 120 mm

Direction: Local +X of the wrist frame

This is a model assumption, not a calibration claim.

The value exists to prove frame math, not physical accuracy.

What Is Being Calculated

Given:

Wrist pose in base frame

Wrist orientation (rotation matrix or equivalent)

Tool offset vector in wrist frame

The software must compute:

TCP_position = Wrist_position + (R_wrist × tool_offset)


Where:

R_wrist is the wrist rotation expressed in base frame

This is pure geometry.

Implementation Artifact
milestone_07_frames.py (Authoritative)

This script must:

Define Base, Wrist, and TCP frames explicitly

Accept a wrist pose (position + orientation)

Apply the tool offset via rotation

Output TCP position in base coordinates

No firmware calls.
No motion.
No shortcuts.

How to Run Milestone 07
Preconditions

Python environment active

No hardware required

No robot motion

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_3_Geometry_and_Rigor/07_coordinate_frames/milestone_07_frames.py

What You Should See

The script should:

Print wrist pose

Print tool offset

Print computed TCP pose

Demonstrate that changing wrist orientation changes TCP position

Example (conceptual):

Wrist Pose:  (300, 0, 200)
Wrist Rot:   45° pitch
Tool Offset: (120, 0, 0)

TCP Pose:    (384.9, 0, 284.9)


Changing the wrist angle must change TCP position.

If it does not, the milestone has failed.

Definition of Done (Acceptance Criteria)

Milestone 07 is DONE only if:

Frame Integrity

Base frame explicitly defined

Wrist frame explicitly defined

TCP frame explicitly defined

Mathematical Correctness

Tool offset is applied via rotation, not addition

Orientation affects TCP position

Results are deterministic

Scope Integrity

No firmware calls

No IK math

No motion commands

No vision input

Observational

Human verifies math matches expectation

Frame logic is understandable and documented

If any condition fails → Milestone 07 FAILS.

Why This Milestone Matters

Without this milestone:

Vision cannot map pixels to motion

TCP accuracy cannot be reasoned about

Tool changes become hacks

IK math becomes meaningless

Milestone 07 is the bridge between motion and perception.

Final Lock Statement

Milestone 07 establishes:

“The system understands where the tool is, not just where the joint is.”

Motion is not required.
Accuracy is not claimed.
Only frame reasoning is proven.