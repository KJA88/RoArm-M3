Milestone 02 — Mechanical Truths & Limit Calibration

Status: LOCKED

Primary Question Answered

What are the human-verified mechanical limits of the revolute joints?

This milestone answers what the hardware can physically do without damage — not what software should do yet.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 01 — Joint authority only

Produces Artifacts For

Milestone 03 — Limit enforcement in the Supervisor

Explicitly NOT Responsible For

Enforcing limits

Modifying control behavior

IK or task-space motion

Trajectories or streaming motion

Autonomy or feedback loops

Gripper or tool behavior

DO NOT (Hard Rules)

Do NOT enforce limits here

Do NOT reintroduce the gripper

Do NOT back-port limits into Milestone 01

Do NOT guess limits from documentation

Violating any rule invalidates Milestone 02.

Intent

Milestone 02 establishes human-verified mechanical truths for the RoArm-M3.

This milestone:

does not control the robot

does not enforce safety

does not implement kinematics

Its sole purpose is to record physical reality so later software can act safely.

All results are treated as authoritative fact.

Relationship to Other Milestones

Milestone 01 proved joints can be intentionally commanded

Milestone 02 records where joints must eventually be refused

Milestone 03 enforces these truths in software

Milestone 02 produces data only, never behavior.

Scope & Constraints
In Scope

Human-in-the-loop mechanical discovery

Slow, incremental joint motion

Observation of:

hard stops

unsafe geometry

torque strain

Recording verified limits to disk

Explicitly Out of Scope

Limit enforcement

IK or task-space motion

Trajectories or streaming

Autonomy or feedback loops

Firmware-reported limits

Gripper or tool behavior

Only observed mechanical reality is accepted.

Joints Covered
Revolute Joints ONLY

This milestone applies only to:

Joint 2 — Shoulder

Joint 3 — Elbow

Joint 4 — Wrist

The gripper (Joint 6) is explicitly excluded.

Calibration Method (Human-Verified)

For each revolute joint:

Start from a neutral midpoint

Jog slowly in the negative direction

Stop when:

mechanical resistance is felt, or

geometry becomes unsafe

Record that value as negative_limit

Repeat in the positive direction

Human confirms:

“This is the safe edge.”

No automation
No symmetry assumptions
No documentation-based guessing

Measurement Instrument (Script Role)
milestone_02_mechanical_truths.py

This script is a measurement instrument, not control logic.

It exists to:

enable torque explicitly

move one joint at a time

prompt the human for confirmation

write results to disk

It must not:

enforce limits

reuse limits

modify supervisor behavior

Output Artifact
joint_limits.json

Written to:

core/calibration/joint_limits.json

Example Entry
{
  "3": {
    "name": "Elbow",
    "negative_limit": -0.366,
    "positive_limit": 3.034,
    "units": "radians",
    "verified_by": "human",
    "milestone": "02_mechanical_truth"
  }
}


This file:

contains revolute joints only

is treated as authoritative mechanical fact

is immutable input for Milestone 03+

How to Run Milestone 02
Preconditions

Milestone 01 complete

RoArm-M3 powered on

USB-to-UART connected

Physical clearance around the arm

Operator present

Run from Repository Root
cd ~/RoArm
source ~/.venv/bin/activate

Execute
python3 milestone_02_mechanical_truths.py


The script will:

enable torque explicitly

walk joints 2, 3, and 4

prompt the human to lock limits

write results to joint_limits.json

Definition of Done (Exit Criteria)

Milestone 02 is complete when:

Joints 2, 3, and 4 each have:

verified negative limit

verified positive limit

Limits are persisted to joint_limits.json

No gripper data exists in the file

Limits are reproducible and trusted by the operator

At this point, mechanical reality is encoded in software.

Limits are NOT enforced yet.
Enforcement begins in Milestone 03.

Two Future Traps (Read This Once)

Never “tweak” limits in code
If a limit is wrong, re-run Milestone 02.

Never assume symmetry
Hardware is not ideal. The file is the truth.