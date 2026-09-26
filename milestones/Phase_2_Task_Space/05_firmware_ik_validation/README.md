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

Historical diagnostic implementation

milestone_05_reachability.py issued task-space commands through SDK pose_ctrl().

That script observed the underlying UART protocol. It is not the current production path.

Current production implementation

Named task probes use HTTP only:

GET http://192.168.4.1/js?json=<JSON command>

Motion uses T:104.

Fresh state and delayed settled verification use T:105, expecting T:1051.

There is no UART or serial fallback.

The HTTP body returned immediately by T:104 is command acceptance only. It is not settled-state verification.

The supervisor does not retry or compensate.

This milestone characterizes behavior. It does not enforce policy.

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

Historical UART diagnostic

The original reachability script expected:

Milestone 04 complete

Z-floor safety interlock active

RoArm-M3 powered on

UART connected

Physical clearance around arm

Human observer present

Run that historical script from the repository root:

cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_2_Task_Space/05_firmware_ik_validation/milestone_05_reachability.py

Current named production probes are not run by that UART script.

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

Default Operational Approach

Normal SYZYGY arm motion uses this sequence:

READY
-> controlled approach
-> target
-> delayed T105 verification
-> eventual vision correction

READY is the default pre-pose.

Another pre-pose may be used only when the task or test explicitly specifies it.

The production skill ready_approach_center performs that default sequence for task_probe_center only:

READY
-> 3 second dwell, the same dwell used by the demonstrated scan
-> fresh T105
-> one named T104
-> 3 second dwell
-> delayed T105

It does not accept arbitrary XYZ or an alternate pre-pose.

ready_approach_center is live physically verified. One run started from the previous X300 state, completed READY, then completed the center T104. Roll and gripper were preserved. There were no retries and no uncertain outcomes. Immediate command responses were not used as final position proof.

The 3 second dwell is not guaranteed fully settled time. Z changed by about +0.480 mm between the built-in delayed T105 and another T105 taken about 6 seconds later. No cause is inferred, and no compensation is applied.

milestone_05_task_probe_authority.py remains the independent diagnostic probe path. The operational skill does not replace it.

A received T104 HTTP response is not position verification. The delayed T105 is recorded separately, and position_verified stays false because no target-match tolerance is claimed.

An AI must not silently choose a different pre-pose.

Z200 -> center and Z300 -> center are experimental approach-direction tests. They are not the normal default.

When approach history matters, record:

starting pose

pre-pose

approach direction

target

delayed settled T105

The immediate T:104 response is not settled-state verification.

Current measurements do not justify Cartesian compensation.

Human / Owner Observations

These observations are physical observations by the owner. They are not firmware readback measurements.

Joints sometimes sag or settle under load.

How a pose is approached matters.

Approaching the same nominal pose from below can behave differently from approaching it from above.

Many joint configurations can achieve the same nominal Z or Cartesian location.

High-acceleration moves can cause the arm to rock mechanically after commanded motion stops. Differences between early and later T105 snapshots may therefore include residual oscillation and must not automatically be interpreted as static sag or drift.

Stored Speed And Acceleration Documentation

These statements come from files already in the repository. They do not change the packets currently sent.

Manufacturer Python API, docs/01_REFERENCE_EXTERNAL/roarm_m3_en.md:

Joint and gripper control functions document speed as an integer in [1, 4096], unit step/s, and acceleration as an integer in [1, 254], unit step/s^2. The opening example uses 1000 step/s and 50 steps/s^2. The joint_radian_ctrl acceleration line is truncated in that file as "step/s^"; the other joint and gripper functions say step/s^2.

pose_ctrl(pose), in section 4, takes only the pose list. That manufacturer section documents no speed parameter and no acceleration parameter.

The manufacturer file does not define spd=0, acc=0, or a JSON T-code mapping.

Internal protocol notes, docs/02_NOTES_INTERNAL/roarm_kinematics_control_log.json:

T101 and T102 templates include spd and acc, with example values spd 0 and acc 10. Those notes do not define the meaning, units, or zero behavior.

The T104 template includes spd, with example value 0.25, and does not include acc. Its note says the command blocks until done. T1041 includes neither spd nor acc.

docs/01_REFERENCE_EXTERNAL/command_cheatsheet.md section 7 shows one T102 example with spd 0 and acc 0. It does not define those fields.

Current production packets:

READY T102 uses spd 0 and acc 0. Those values match the cheatsheet example. They are outside the only numeric ranges documented by the manufacturer joint API, and this repository does not document what zero means.

Named T104 uses spd 0.5. That value is inherited from milestone_04_supervisor.py and milestone_05_reachability.py. The manufacturer pose_ctrl section does not document it. The internal T104 note does not define its unit or say that a lower value is gentler.

Demonstrated base-scan T101 uses spd 200 and acc 10. Those numbers lie inside the manufacturer joint ranges [1, 4096] and [1, 254]. The stored files do not say that this scan packet was selected from those ranges, and they do not define its motion as slower or gentler.

No stored manufacturer section documents a supported T104 acceleration field. No stored section documents that lowering spd or acc reduces post-stop rocking.

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