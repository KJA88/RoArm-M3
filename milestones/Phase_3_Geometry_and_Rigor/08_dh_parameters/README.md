Milestone 08 — Denavit–Hartenberg Parameters

Phase: 3 — Geometry & Rigor
Status: IN PROGRESS → LOCKABLE

Primary Question Answered

Can the robot’s kinematic chain be expressed as a formal Denavit–Hartenberg (DH) model that reproduces the arm’s geometry in a mathematically consistent way?

This milestone proves model correctness, not motion capability.

Authority & Dependency Rules
Consumes Artifacts From

Milestone 07 — Explicit coordinate frames & TCP reasoning

Milestone 02 — Mechanical joint limits (as reference only)

Produces Guarantees For

Milestone 09 — Custom IK vs firmware IK comparison

Phase 4 — Vision → world → TCP mapping

Phase 5 — Planning & autonomy

Explicitly NOT Responsible For

Moving the robot

Streaming trajectories

Enforcing joint limits

Firmware communication

Accuracy validation against hardware

Closed-loop control

DO NOT

Call firmware IK

Use pose_ctrl

“Tune” DH parameters to match firmware behavior

Skip frame definitions

Assume planar simplifications

Violating any of the above invalidates Milestone 08.

Intent

Milestone 08 establishes mathematical authority over the robot’s structure.

Up to now:

Motion was empirical

Safety was procedural

Behavior was observed

From this point on:

Geometry must be provable

Frames must be explicit

Transforms must be derivable

This milestone answers:

“Can we describe this robot using first-principles kinematics?”

No motion is required.

What This Milestone Is (and Is Not)
This Milestone IS

A formal kinematic description

A table of DH parameters

A reproducible forward kinematics (FK) computation

A mathematical contract

This Milestone IS NOT

Inverse kinematics

Firmware replication

Calibration

Optimization

Control

DH Convention Used

This milestone must explicitly choose one convention:

Standard DH or

Modified DH

⚠️ The chosen convention must be:

Stated clearly

Used consistently

Never mixed

(Changing conventions later requires a new milestone.)

Frames Covered

The DH model must cover:

Base frame {B}

All revolute joints in sequence

Wrist frame {W}

Tool Center Point {T} (via fixed offset from Milestone 07)

Each frame must be explicitly represented.

Required DH Table

The DH table must include, per joint:

Joint	aᵢ	αᵢ	dᵢ	θᵢ	Units

Units must be explicit (mm / radians)

Fixed vs variable parameters must be identified

Tool offset must not be hidden inside joint parameters

What Is Being Proven

Given:

A joint configuration vector q

A DH parameter table

The software must compute:

T_base_to_tcp(q)


Such that:

Transform composition is correct

Orientation propagates correctly

Tool offset is applied in the correct frame

This is pure math.

Implementation Artifacts
milestone_08_dh_model.py (Authoritative)

This script must:

Define the DH table

Implement homogeneous transforms

Chain transforms base → TCP

Print or return the final transform

Demonstrate repeatability

No hardware.
No firmware.
No shortcuts.

How to Run Milestone 08
Preconditions

Python environment active

Milestone 07 complete

No robot required

Run From Repository Root
cd ~/RoArm
source ~/.venv/bin/activate
python3 milestones/Phase_3_Geometry_and_Rigor/08_dh_parameters/milestone_08_dh_model.py

What You Should See

The script should output:

The DH table

One or more test joint configurations

The resulting base → TCP transform

Example (conceptual):

Joint Configuration: [0.0, 0.5, -0.3, 0.0]
TCP Position: (312.4, 18.2, 201.7)
TCP Orientation: RPY = (0.0, 0.2, 0.0)


Running the script multiple times with the same input must produce identical output.

Definition of Done (Acceptance Criteria)

Milestone 08 is DONE only if:

Mathematical Integrity

DH convention explicitly stated

DH table fully defined

Homogeneous transforms implemented correctly

Tool offset handled as a separate transform

Repeatability

Same input → same output

No randomness

No hidden state

Scope Integrity

No firmware calls

No motion commands

No IK logic

No calibration logic

Documentation

DH parameters documented

Frame meanings explained

Assumptions clearly stated

If any condition fails → Milestone 08 FAILS.

Why This Milestone Matters

Without Milestone 08:

IK cannot be validated

Vision cannot map to motion

Tool changes become hacks

Firmware behavior cannot be audited

Milestone 08 is where intuition becomes math.

Final Lock Statement

Milestone 08 establishes:

“The robot’s geometry is formally defined and mathematically reproducible.”

Accuracy is not claimed.
Firmware agreement is not claimed.
Only geometric consistency is proven