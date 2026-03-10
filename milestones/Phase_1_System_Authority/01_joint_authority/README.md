Milestone 01 — Joint Authority & Safety

Status: LOCKED

Primary Question Answered

Can software intentionally and safely command individual joints in joint space with no hidden or coupled behavior?

If the answer to this question is not yes, no higher-level behavior is trusted.

Authority & Dependency Rules
Consumes Artifacts From

NONE

Produces Guarantees For

Milestone 02 — Mechanical discovery (limits, range)

Milestone 03 — Deterministic enforcement and pipelines

Explicitly NOT Responsible For

Mechanical limit calibration

Mechanical limit enforcement

Inverse kinematics (IK)

Task-space motion (X, Y, Z)

Trajectories or streaming motion

Autonomy or feedback loops

Gripper or tool characterization

DO NOT (Hard Rules)

Do NOT load joint_limits.json

Do NOT enforce limits

Do NOT back-port Milestone 02 knowledge

Do NOT add task-space logic

Violating any of the above invalidates Milestone 01.

Intent

Milestone 01 establishes direct joint-space authority over the RoArm-M3.

The goal is to prove that the Raspberry Pi can:

Open a UART connection to the arm

Explicitly enable torque

Command exactly one joint at a time, in radians

Do so intentionally, safely, and reversibly

Observe behavior directly (human-in-the-loop)

This milestone is joint-space only.

No inverse kinematics
No task-space (X, Y, Z)
No trajectories

If Milestone 01 is not solid, nothing higher-level is trusted.

Files and Their Roles
Infrastructure (Not the Test)
core/supervisor/mechanical_supervisor.py

This file is infrastructure, not the milestone itself.

It exists to:

Open and manage the UART connection

Explicitly enable torque (T=210)

Send isolated joint commands

Prevent implicit or background motion

Provide a clean shutdown path

All joint motion must pass through this supervisor.
No ad-hoc scripts may command joints directly.

Verification (This Is the Milestone)

Milestone 01 is verified by running a human-observed single-joint motion test
using the MechanicalSupervisor.

This is intentionally simple and manual.

The goal is proof of authority, not automation.

Scope & Constraints
In Scope

UART communication with the arm

Explicit torque enable using firmware command T=210

Direct joint commands using T=102

One joint moved per command

Human-observed safety validation

Explicitly Out of Scope

Mechanical limit calibration

Joint limit enforcement

IK or task-space control

Trajectories or streaming motion

Autonomy or feedback loops

Those come later.

Hardware Laws Enforced (Milestone 01 Level)
Torque Discipline

Torque is enabled explicitly using:

{ "T": 210, "cmd": 1 }


Torque is never enabled implicitly

Torque is never toggled automatically during motion

Torque is disengaged only during explicit shutdown

Single-Joint Isolation

Each command moves exactly one joint

All other joints remain stationary

No residual or coupled motion is allowed

No background behavior is permitted

At this milestone, mechanical limits are NOT enforced.
Only intentional control is proven.

How to Run Milestone 01 (Authoritative Procedure)
Preconditions

RoArm-M3 powered on

USB-to-UART cable connected

Arm has full physical clearance

Operator is present and watching the arm

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate   # if applicable

Test: Single-Joint Authority (Example: Elbow)
from core.supervisor.mechanical_supervisor import MechanicalSupervisor
import time

arm = MechanicalSupervisor()

# Move exactly one joint (Joint 3: Elbow)
arm.move_joint(3, 0.5)
time.sleep(1)
arm.move_joint(3, 0.0)

arm.close()

Expected Behavior (PASS CONDITIONS)

Only the elbow joint moves

No other joints move

No gripper motion

Torque remains enabled during motion

Torque disengages on shutdown

No errors are reported

Failure Conditions (ANY = FAIL)

Any joint other than the target joint moves

Torque enables without an explicit command

Torque remains enabled after shutdown

Motion occurs without a direct command

Coupled or background motion is observed

If any failure condition occurs, Milestone 01 has failed and must be corrected before proceeding.

Milestone Outcome

When this procedure passes:

Joint commands are trusted

Joint motion is isolated

Torque behavior is explicit

Higher-level logic may assume honest joint control

Milestone 01 may then be declared:

LOCKED