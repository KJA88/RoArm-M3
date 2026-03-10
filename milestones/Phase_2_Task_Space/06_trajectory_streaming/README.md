Milestone 06 — Trajectory Streaming

Status: IN PROGRESS → LOCKABLE

Primary Question Answered

Can the system issue a sequence of task-space commands fast enough that motion is continuous, smooth, and deterministic — rather than discrete pose “teleportation”?

This milestone proves temporal authority, not geometric correctness.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 03 — Deterministic command/response pipeline

Milestone 04 — Task-space safety gating

Milestone 05 — Firmware IK behavior characterization

Produces Guarantees For

Phase 3 — Kinematics & math authority

Phase 4 — Vision-guided motion

Phase 5 — Autonomy and state machines

Explicitly NOT Responsible For

IK correctness

Positional accuracy

Path optimality

Obstacle avoidance

Vision feedback

Closed-loop control

Error correction

DO NOT

Enforce workspace limits beyond M04

“Fix” firmware IK errors

Assume Cartesian accuracy

Blend perception into motion

Add math models

Violating any of the above invalidates Milestone 06.

Intent

Milestone 06 establishes continuous task-space motion.

Up to now, the system has only proven it can:

Think in XYZ

Gate unsafe commands

Observe firmware behavior

Now it must prove:

“I can send XYZ commands frequently enough that the arm never fully stops between them.”

This is the difference between:

issuing poses

and commanding motion

Key Concept: Streaming vs. Teleporting
Teleporting (What Came Before)

One pose command

Arm moves

Arm stops

Next pose

This is acceptable for validation, not motion.

Streaming (What This Milestone Proves)

A sequence of small task-space steps

Issued at a fixed cadence

Arm is always in motion

No visible pauses

Deterministic timing preserved

The arm should feel like it is following a curve, not hopping between points.

Protocol Scope

Task-space commands are issued using a single consistent task-space opcode

(e.g. T:101, T:1041, or firmware-specific equivalent)

Exact opcode is documented, not assumed

Timing cadence is software-controlled

Supervisor remains authoritative

⚠️ This milestone does not decide which opcode is “correct forever”
It proves continuous behavior is possible.

Trajectory Definition
Geometric Test: Converging Spiral (Planar)

Motion occurs in X and Y

Z remains constant and safely above floor

Radius decreases smoothly over time

Why a spiral?

Continuous curvature

Direction changes

No straight-line cheating

Exposes stutter immediately

Timing Requirements

Target update rate: ~33 Hz

Interval: ~30 ms between commands

Jitter must be visibly negligible

This is a temporal test, not a speed test.

Implementation Artifacts
milestone_06_trajectory.py (Authoritative)

This script:

Generates a task-space spiral

Breaks it into small XYZ steps

Issues commands at a fixed cadence

Preserves M03 handshake discipline

Obeys M04 Z-floor gating

No perception.
No correction.
No math beyond generating the curve.

How to Run Milestone 06
Preconditions

Milestones 00–05 complete

Z-floor safety active

Firmware behavior understood

Physical clearance around arm

Human observer present

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_2_Task_Space/06_trajectory_streaming/milestone_06_trajectory.py

What You Should See (This Is Critical)
Expected Physical Behavior

Arm begins moving immediately

Motion is continuous

No stop-and-go behavior

Path looks smooth and spiral-like

Z height remains constant

No table contact

No torque drops

If the arm visibly pauses between steps → FAIL

Expected Console Behavior

Regular command issuance logs

No command backlog

No missed responses

No timeouts

No emergency stops

Definition of Done (Acceptance Criteria)

Milestone 06 is DONE only if:

Temporal

Commands issued at fixed cadence

No visible pauses in motion

Arm never fully stops mid-path

Behavioral

Deterministic handshake preserved

Z-floor gating still enforced

No firmware crashes

No torque dropouts

Observational

Human confirms smooth motion

Spiral path is recognizable

Motion feels continuous, not stepped

Scope Integrity

No IK math added

No correction logic added

No perception added

If any of these fail → Milestone 06 FAILS.

What This Milestone Enables

After Milestone 06:

The system can express motion, not just poses

Vision can guide motion later

State machines can sequence actions

Math models can be validated meaningfully

This is the last “pure motion” milestone.

# LOCK STATEMENT:
# Milestone 06 is complete. Continuous task-space streaming motion has been
# demonstrated without stop-and-go behavior under Supervisor timing control.
Continuous motion was visually verified using a 33 Hz spiral trajectory with no observable pauses.