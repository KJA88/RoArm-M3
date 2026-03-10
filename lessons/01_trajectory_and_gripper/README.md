## Lesson 01 – Cartesian Trajectory Streaming & Gripper Control

### Intent

This lesson establishes **foundational control authority** over the RoArm-M3 Pro.

It proves that the robot can be:

- Driven directly in **Cartesian (task) space**, not joint space.
- Controlled using the firmware’s **internal inverse kinematics** (T=104 / T=1041).
- Streamed along **continuous, real-time trajectories** at a fixed update rate.
- Operated safely with **explicit gripper limits and state discipline**.

This is not a visualization or replay lesson.  
It is a **real-time motion control** lesson.

All commands are run from the repo root:

```bash
cd ~/RoArm
Demo Scripts (Lesson 01 Showcase)
Lesson 01 intentionally includes only a small number of high-signal demos.
Each demo exists to prove a specific control capability.

1. Parametric Lissajous Trajectory (Primary Demo)
Script:
lessons/01_trajectory_and_gripper/demo_lissajous.py

This demo streams a smooth 3D parametric figure-eight (Lissajous) trajectory in Cartesian space.

What it does:

Torques the arm on.

Moves to a known start pose using a blocking Cartesian move (T=104).

Streams a time-parameterized Cartesian trajectory using T=1041 at a fixed rate.

Generates coordinated X, Y, and Z motion from analytic parametric equations.

Returns the arm to a known, safe neutral pose.

What this demonstrates:

Task-space control without manual joint angle planning.

Stable real-time streaming (no stop-and-go motion).

Trust in the firmware’s IK under continuous motion.

Deterministic, repeatable trajectories driven from Python.

Run:

bash
Copy code
python3 lessons/01_trajectory_and_gripper/demo_lissajous.py
2. Constant-Speed Parametric Trajectory (Advanced Control)
Script:
lessons/01_trajectory_and_gripper/demo_lissajous_constant_speed.py

This demo executes the same geometric Lissajous path as the primary demo, but re-parameterized to maintain approximately constant end-effector speed along the curve.

What it adds beyond the basic Lissajous demo:

Separation of path geometry from motion timing.

Approximate arc-length normalization to reduce velocity variation.

Visually uniform motion through high-curvature regions.

What this demonstrates:

Understanding of time-vs-distance effects in trajectory generation.

Motion planning concepts used in industrial robot controllers.

Attention to motion quality, not just path correctness.

This demo exists specifically to show motion intelligence, not just math.

Run:

bash
Copy code
python3 lessons/01_trajectory_and_gripper/demo_lissajous_constant_speed.py
3. Volumetric Spiral / Helix Trajectory
Script:
lessons/01_trajectory_and_gripper/demo_spiral.py

This demo streams a volumetric spiral / helix through Cartesian space.

What it does:

Uses continuous streaming (T=1041) to coordinate X, Y, and Z motion.

Demonstrates controlled motion through a 3D volume, not a plane.

Emphasizes smooth vertical modulation alongside planar motion.

What this demonstrates:

True 3D task-space thinking.

Coordinated multi-axis motion under streaming control.

Trajectory generation suitable for operations like insertion, scanning, or surface following.

Run:

bash
Copy code
python3 lessons/01_trajectory_and_gripper/demo_spiral.py
Gripper Control & Safety Utilities
Lesson 01 also establishes safe, reusable gripper control, which all later lessons depend on.

High-Level Gripper Interface
Script:
lessons/01_trajectory_and_gripper/roarm_gripper.py

Provides a small Python abstraction for gripper control:

Maps intuitive “open / close” intent to servo angle commands.

Enforces hard safety limits to prevent stalling or buzzing.

Designed to be imported by all motion scripts.

Example usage:

python
Copy code
from lessons.01_trajectory_and_gripper.roarm_gripper import set_gripper

set_gripper(ser, angle_rad=2.8)  # nearly closed, within safe range
Gripper Characterization Utility
Script:
lessons/01_trajectory_and_gripper/gripper_sweep.py

This utility was used to empirically determine safe operating limits.

It:

Sweeps the gripper through a range of angles.

Allows visual confirmation of:

Fully open

Light pinch

Near-stall regions

Informs the safety limits enforced by roarm_gripper.py.

Run:

bash
Copy code
python3 lessons/01_trajectory_and_gripper/gripper_sweep.py
Safety note:
Keep fingers clear. Stop immediately if the gripper stalls or audibly buzzes.

Lesson 01 Takeaways
After completing Lesson 01:

You can command a real 6-DOF robot arm directly in Cartesian space.

You understand blocking vs streamed motion (T=104 vs T=1041).

You can generate continuous, real-time trajectories from Python.

You account for motion quality, not just endpoint accuracy.

You enforce explicit safety limits when controlling hardware.

Portfolio / interview summary:

“I implemented real-time Cartesian trajectory streaming (parametric and volumetric paths) with safe gripper control on a 6-DOF robot arm, using firmware-level inverse kinematics and streamed motion commands over UART.”

Lesson 01 is the control foundation for all subsequent work:
vision, calibration, tracking, and autonomous manipulation.