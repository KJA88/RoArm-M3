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

The production task-space command on this arm is HTTP T104. Current Waveshare pose_ctrl emits T1041, which the control wiki describes as the fastest uninterpolated goal. Milestone 09 compares geometry with observed firmware behavior. It does not switch that production command. Official URDF and host IK candidates are recorded in docs/01_REFERENCE_EXTERNAL/waveshare_official_reuse_audit.md.

Observe reported joint angles or end pose

Record outcome

Custom IK Path

Use DH model to solve IK in Python

Produce joint angle solution(s)

Forward-solve to TCP for validation

No enforcement.
No correction.
Just comparison.

Upstream Waveshare FK Against Recorded T105

This comparison uses the analytical FK in waveshareteam/roarm_ws commit fc2b0e40, solver.hpp namespace roarm_m3, with the published lengths. No length or offset was fitted. No hardware was moved. IK is not part of this result.

The historical fitted planar model is a different model. Its fit is L1 238.839 mm, L2 316.731 mm, X0 −0.186 mm, Z0 −0.371 mm, shoulder_offset 0.126072 rad, elbow_offset −0.085031 rad. runtime/core/calibration/planar_calib.json is a sketch with L1 236, L2 145, L3 175 and zero offsets. That sketch is not the fit, and this comparison does not use either planar file.

Reported joints in, upstream FK out. Signed error is the upstream prediction minus the T105 firmware-reported Cartesian pose. T105 x, y, z, and tit are that firmware report. They are not an independently measured physical TCP position. The numerical agreement supports that this report is computed from the reported joints by the Waveshare FK or an algebraically equivalent model. It does not prove that the firmware source file is solver.hpp.

| Pose | Reported b, s, e, t | T105-reported x, y, z, tit | FK x, y, z, pitch | dx, dy, dz mm | XYZ mm | Pitch rad |
| --- | --- | --- | --- | --- | --- | --- |
| READY | −0.001533981, −0.829883606, 2.405281875, 0.016873789 | 161.3352596, −0.247485383, 163.9417706, 0.021475731 | 161.3353, −0.2475, 163.9418, 0.02148 | 7.3e-8, −3.4e-8, 7.9e-8 | 1.1e-7 | 2.1e-10 |
| CANDLE | −0.004601942, 0.001533981, 0.006135923, 0.001533981 | 46.7404, −0.2151, 552.7962, −1.56159 | 46.7404, −0.2151, 552.7962, −1.56159 | −1.1e-5, 1.9e-6, −1.9e-5 | 2.1e-5 | −2.4e-6 |
| CENTER | −0.001533981, −0.391165101, 1.768679848, 0.228563137 | 250.3220502, −0.383989517, 238.3865744, 0.035281558 | 250.3221, −0.3840, 238.3866, 0.03528 | 1.6e-8, −5.3e-8, 2.0e-7 | 2.1e-7 | −7.9e-10 |
| Z200 | −0.001533981, −0.394233062, 2.089281833, −0.099708751 | 251.3942329, −0.385634226, 194.3709341, 0.024543693 | 251.3942, −0.3856, 194.3709, 0.02454 | 6.5e-8, −5.3e-8, −1.7e-7 | 1.9e-7 | 2.1e-10 |
| Z300 | −0.001533981, −0.305262177, 1.339165228, 0.573708815 | 252.6484006, −0.387558097, 288.7903948, 0.036815539 | 252.6484, −0.3876, 288.7904, 0.03682 | −3.3e-8, −5.3e-8, −9.2e-8 | 1.1e-7 | 2.1e-10 |
| X300 | −0.001533981, −0.181009733, 1.61681575, 0.188679637 | 300.7399995, −0.461329743, 234.9144945, 0.053689328 | 300.7400, −0.4613, 234.9145, 0.05369 | −4.2e-8, −6.4e-8, 1.3e-7 | 1.5e-7 | −7.9e-10 |

READY through X300 are the full-precision m05 records. CANDLE was supplied rounded to 0.0001 mm and 1e-5 rad, and its residual sits at that rounding. The residual does not grow from READY to X300.

Explicit convention trials, worst XYZ error across the six poses:

| Trial | Worst XYZ mm |
| --- | --- |
| Published joint signs | 2.1e-5 |
| Flip base | 0.923 |
| Flip shoulder | 339.432 |
| Flip elbow | 627.100 |
| Flip wrist | 186.940 |
| Add unused solver L1, 126.06 mm, to Z | 126.060 |
| Add URDF base stack, 123.559 mm, to Z | 123.559 |

Pitch `s + e + t − π/2` matches `tit`. Using `s + e + t` without that subtraction misses by up to 1.571 rad. Negating the upstream pitch misses by up to 3.123 rad. No second frame or tool correction was applied. The published map is the one that lines up.

Every recorded base angle is a few thousandths of a radian, and measured |y| is under 0.5 mm. The published base sign agrees with that small Y. This set does not exercise a large yaw.

Replacing the recorded READY wrist 0.016873789 with 0.0015 moves the FK point by 2.648 mm. The comparison uses the recorded wrist.

The upstream FK reproduces the T105 firmware-reported Cartesian pose of these joint states to numerical precision. That is evidence about the firmware report, not evidence that an external measurement of the physical TCP landed on those coordinates. The historical 5.219 mm figure remains the result of a different test: planar IK of the commanded point (235, 0, 234), executed on the arm, with refine leaving that error unchanged.

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