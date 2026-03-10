Milestone 05 — Firmware IK Validation & Workspace Characterization

Status: COMPLETE / LOCKABLE (after criteria below are met)

Primary Question Answered

What task-space commands does the RoArm-M3 firmware IK solver accept, reject, clamp, or ignore — and how does it behave at the edges of physical reachability?

This milestone does not assume correctness.
It measures and documents behavior.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 03 — Deterministic command/response pipeline

Milestone 04 — Task-space semantics and safety gating

Produces Guarantees For

Milestone 06 — Trajectory streaming

Phase 3 — Formal kinematic modeling and audits

Explicitly NOT Responsible For

Implementing inverse kinematics

Correcting firmware IK behavior

Enforcing workspace limits

Streaming trajectories

Cartesian accuracy guarantees

Mathematical modeling

DO NOT

Add custom IK math

“Fix” unreachable poses

Assume solver correctness

Hide or suppress failure cases

Any violation invalidates Milestone 05.

Intent

Milestone 05 treats the firmware IK solver as a black-box physical system.

The goal is not to make the arm move reliably —
the goal is to learn how the firmware behaves.

This milestone establishes workspace awareness by observing:

Which XYZ poses succeed

Which poses fail

Which poses are silently clamped

Which poses are ignored

How the firmware reports each outcome

The Supervisor remains passive and observational.

What “Reachability” Means Here

Reachability is defined empirically, not mathematically.

A pose is considered:

Reachable → firmware executes motion and reports success

Unreachable → firmware rejects, errors, or refuses motion

Clamped → firmware moves, but not to requested XYZ

Ignored → firmware acknowledges but does not move

All four outcomes are valid data.

Protocol Scope

Task-space commands are issued via SDK pose_ctrl()

Underlying UART protocol is observed, not assumed

Any required initialization, delays, or mode changes are logged

The Supervisor does not retry or compensate

This milestone characterizes behavior, it does not enforce policy.

Implementation Artifacts
milestone_05_reachability.py

This file is a diagnostic probe, not a controller.

It:

Issues a predefined set of task-space poses

Waits for deterministic responses (Milestone 03)

Queries pose feedback where available

Logs all results verbatim

No filtering.
No smoothing.
No interpretation at runtime.

Test Space Definition

The test set must include all of the following categories:

1. Known-Safe Interior Points

Clearly reachable XYZ poses

Far from boundaries

Used to confirm baseline operation

2. Boundary Probes

Near max reach in +X, −X, +Y, −Y, +Z

Designed to explore solver edges

3. Impossible Points

Clearly outside physical reach

Used to observe rejection behavior

4. Ambiguous Points

Points that might be solvable mathematically

Used to detect clamping or silent correction

How to Run Milestone 05
Preconditions

Milestone 04 complete

Z-floor safety interlock active

RoArm-M3 powered on

UART connected

Physical clearance around arm

Human observer present

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_2_Task_Space/05_firmware_ik_validation/milestone_05_reachability.py

What You Should See
During Execution

For each test pose:

Supervisor logs:

Requested XYZ

Firmware response

Reported pose (if available)

Motion may or may not occur

Some poses should fail

Some poses may move unexpectedly

Some poses may partially move

⚠️ Failure is expected and required.

If everything “just works,” the milestone has failed.

Output Artifact (Authoritative)
m05_results.json

This file must contain, per test:

{
  "requested_pose": { "x": 300, "y": 0, "z": 200, "pitch": 0 },
  "firmware_response": "...raw response...",
  "reported_pose": { "...": "if available" },
  "observed_behavior": "moved | rejected | clamped | ignored",
  "notes": "human observations"
}


This file is treated as ground truth for future phases.

Definition of Done (Acceptance Criteria)

Milestone 05 is DONE only if all conditions are met:

Data Completeness

Multiple reachable poses tested

Multiple unreachable poses tested

Boundary cases included

Failures are recorded, not suppressed

Behavioral Integrity

Supervisor does not retry or override

Deterministic handshake preserved

Z-floor remains enforced

Torque discipline remains intact

Observational Truth

At least one pose fails

At least one pose behaves unexpectedly

Results are logged verbatim

Human confirms behavior matches logs

Artifacts

m05_results.json exists

Results are reproducible

No enforcement logic added

If any condition is missing → Milestone 05 FAILS.

What This Milestone Enables

After Milestone 05:

You know the true workspace envelope

You know how firmware fails

You know what errors look like

You can stream trajectories safely (M06)

You can audit firmware math later (Phase 3)

This is where ignorance turns into measured knowledge.

Final Lock Statement

Milestone 05 establishes:

“Firmware IK behavior is empirically documented and no longer assumed.”

No guarantees are made.
Only observations are trusted.

With this milestone complete, trajectory streaming is allowed.