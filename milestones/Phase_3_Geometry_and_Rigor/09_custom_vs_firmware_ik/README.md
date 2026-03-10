Milestone 09 — Custom IK vs Firmware IK

Phase: 3 — Geometry & Rigor
Status: IN PROGRESS → LOCKABLE

Primary Question Answered

How does a mathematically derived inverse kinematics (IK) solution compare to the RoArm-M3 firmware’s internal IK solver, and where do they agree or diverge?

This milestone proves analytical understanding, not control superiority.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 08 — Formal DH parameterization

Milestone 05 — Empirical firmware IK behavior

Milestone 07 — Frame & TCP correctness

Produces Guarantees For

Phase 4 — Vision-guided alignment

Phase 5 — Planning, autonomy, and decision logic

Future decision: Firmware IK vs Custom IK authority

Explicitly NOT Responsible For

Enforcing motion

Choosing a “winner”

Replacing firmware IK

Streaming trajectories

Closed-loop correction

Real-time performance

DO NOT

Tune custom IK to match firmware behavior

Assume firmware IK is correct

Assume custom IK is correct

Use perception input

Hide discrepancies

Violating any of the above invalidates Milestone 09.

Intent

Up to now:

Firmware IK was treated as a black box

Geometry was proven independently

Errors were observed but not explained

Milestone 09 brings those two worlds together.

The goal is not to fix anything.

The goal is to answer:

“If I ask both systems the same geometric question, what do they say?”

This milestone establishes epistemic authority:

What the firmware does

What the math predicts

Where reality diverges

What Is Being Compared

For a given task-space pose {X, Y, Z, Pitch}:

Firmware IK Path

Command pose via pose_ctrl()

Observe reported joint angles or end pose

Record outcome

Custom IK Path

Use DH model to solve IK in Python

Produce joint angle solution(s)

Forward-solve to TCP for validation

No enforcement.
No correction.
Just comparison.

Test Case Definition

The test set must include:

1. Clearly Reachable Poses

Central workspace

Expected to be solvable by both systems

2. Boundary Poses

Near physical limits

Expected to stress solver assumptions

3. Ambiguous Poses

Multiple IK solutions possible

Used to reveal solver preferences

4. Unreachable Poses

Outside physical envelope

Used to compare failure modes

Implementation Artifacts
milestone_09_compare_ik.py (Authoritative)

This script must:

Define a list of test poses

Solve IK analytically using Milestone 08 DH model

Query firmware IK behavior for the same pose

Forward-solve both results

Log discrepancies

No motion streaming.
No retries.
No filtering.

How to Run Milestone 09
Preconditions

Milestones 00–08 complete

Firmware behavior characterized (M05)

Python DH model available

Human observer present (for firmware motion)

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_3_Geometry_and_Rigor/09_custom_vs_firmware_ik/milestone_09_compare_ik.py

Output Artifacts (Authoritative)
m09_ik_comparison.json

Each test case must include:

{
  "requested_pose": { "x": 250, "y": 0, "z": 200, "pitch": 0 },
  "custom_ik_solution": {
    "joint_angles": [...],
    "fk_tcp": { "...": "..." }
  },
  "firmware_ik_result": {
    "reported_pose": { "...": "..." },
    "observed_behavior": "executed | clamped | refused"
  },
  "discrepancy": {
    "position_error_mm": 123.4,
    "orientation_error_rad": 0.42
  },
  "notes": "observed singularity near wrist"
}


This file is truth, not opinion.

Definition of Done (Acceptance Criteria)

Milestone 09 is DONE only if:

Comparison Integrity

Same pose tested in both systems

Custom IK uses DH model only

Firmware IK treated as opaque

Observational Truth

Discrepancies are logged

Failures are recorded, not hidden

Multiple outcomes observed

Scope Integrity

No enforcement logic added

No tuning to match results

No motion planning added

Documentation

Comparison results saved

Behavioral patterns noted

Known failure modes identified

If any condition fails → Milestone 09 FAILS.

Why This Milestone Matters

Milestone 09 answers a question most robotics projects never answer honestly:

“Do we trust the firmware because it’s right — or because we never checked?”

After this milestone:

Firmware IK can be trusted conditionally

Custom IK can be validated contextually

Planning decisions can be grounded in reality

Final Lock Statement

Milestone 09 establishes:

“Firmware IK behavior is understood relative to first-principles geometry.”

No solver is crowned.
No authority is assumed.
Only comparison is proven.

Phase 3 Exit Condition

With Milestone 09 complete:

Geometry is explicit

Math is formal

Firmware behavior is contextualized

Phase 4 (Perception) may begin.