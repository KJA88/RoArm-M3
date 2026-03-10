Milestone 04 — Task-Space Experiments & Task-Space Authority

Status: COMPLETE / LOCKABLE

Primary Question Answered

Can the Supervisor reason about Cartesian (X,Y,Z) commands and prevent physically dangerous motion before commands reach the firmware?

This milestone proves task-space awareness and gating, not full task-space control.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 03 — Deterministic command/response pipeline

Produces Guarantees For

Milestone 05 — Firmware IK validation

Milestone 06 — Trajectory streaming

Explicitly NOT Responsible For

IK solver correctness

Reachability validation

Cartesian accuracy

Error measurement

Streaming performance

Trajectory smoothness

Autonomy

DO NOT

Trust firmware IK

Measure accuracy

Enforce joint limits

Add math models

Assume Cartesian correctness

Violating any of the above invalidates Milestone 04.

Intent

Milestone 04 transitions the system from joint-space thinking (radians) to
task-space thinking (X, Y, Z) — without trusting the firmware.

This milestone establishes the Raspberry Pi Supervisor as a Cartesian Gatekeeper.

The Supervisor must:

Inspect task-space commands

Reason about physical safety

Block dangerous motion before hardware execution

Preserve deterministic command flow (Milestone 03)

This is the first milestone where software is allowed to say “NO” to motion.

Coordinate Frame Definition (Experimental Authority)

This milestone defines a working task-space frame for experimentation:

Origin (0,0,0): Center of arm base

X: Forward (+) / Backward (−)

Y: Left (+) / Right (−)

Z: Up (+) / Down (−)

⚠️ These definitions are experimental, not yet validated against firmware truth.
They exist to enable safe exploration, not correctness claims.

The Mechanical Truth Introduced Here: Safety Floor
Z-Axis Software Interlock

This milestone introduces the first software-enforced physical rule:

Z-Floor: Z ≥ 20.0 mm

Why This Exists

Prevent table collision

Prevent firmware misinterpretation

Prevent spiral/trajectory tests from self-destructing

Enable safe experimentation in Milestones 05–06

Enforcement Rule
If requested Z < 20.0 mm:
    Block command
    Log rejection
    Do NOT transmit to firmware


This rule is enforced in the Supervisor, not the firmware.

Implementation Artifacts
milestone_04_supervisor.py

This file:

Inherits deterministic handshake behavior from Milestone 03

Accepts task-space commands (X,Y,Z)

Applies the Z-floor interlock

Executes a known, bounded task-space spiral

This is not a general controller.
It is a controlled experiment harness.

How to Run Milestone 04
Preconditions

Milestone 03 complete

RoArm-M3 powered on

UART connected

Physical clearance around arm

Human operator present

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_2_Task_Space/04_task_space_experiments/milestone_04_supervisor.py

What You Should See (This Matters)
On Startup

Supervisor initializes

Deterministic handshake confirmed

Torque explicitly enabled

Task-space mode announced

The arm should not move immediately.

During Execution

The script executes a bounded spiral in task space.

You should observe:

Smooth, deliberate motion

Z remains ≥ 20 mm at all times

Motion pauses between commands

No jumps

No torque drops

Critical Proof Moment

At least one planned spiral point would descend below Z = 20 mm if ungated.

What must happen:

Supervisor logs a blocked command

That command is not sent

The arm does not descend

Execution continues safely

This moment is the entire milestone.

Expected Console Output (Conceptual)

Exact strings don’t matter — behavior does.

You should see logs similar to:

[M04] Supervisor Online
[M04] Task-space experiment active
[M04] Executing spiral trajectory
[M04] Z-floor violation blocked: Z=12.6
[M04] Continuing safe execution


If no blocking occurs, the milestone has failed.

Definition of Done (Acceptance Criteria)

Milestone 04 is DONE only if all conditions are met:

Functional

Task-space (X,Y,Z) commands are used

No joint-space commands issued directly

Supervisor inspects all Cartesian requests

Safety

Z-floor (20 mm) is enforced

Unsafe commands are blocked

Firmware never receives blocked commands

Behavioral

Deterministic handshake preserved

Motion is intentional and controlled

Torque remains enabled during motion

Torque disengages on exit

Observational

Arm never contacts table

Human confirms blocked descent

Logs clearly indicate intervention

If any of these fail → Milestone 04 FAILS.

What This Milestone Enables

After Milestone 04:

The Pi can safely experiment in task space

Firmware IK can be tested without blind trust

Failure cases can be observed safely

Trajectories can be attempted without collisions

This milestone is the safety bridge between authority and characterization.

Final Lock Statement

Milestone 04 establishes:

“The Supervisor understands task-space intent and may veto unsafe motion.”

No correctness claims are made.
No IK trust is assumed.

With this milestone complete, Milestone 05 is allowed to begin