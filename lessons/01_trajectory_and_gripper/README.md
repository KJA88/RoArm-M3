## Lesson 01 – Trajectory Streaming & Gripper Control

**Intent**

This lesson proves that the RoArm-M3 Pro can be:

- Driven in **task space** using the firmware’s internal IK (T=104 / T=1041).
- Streamed along smooth **line/circle trajectories**.
- Controlled at the **gripper** level safely (open/close sweeps, angle mapping).

This is your “I can actually move a real robot arm in a controlled way” lesson.

All commands are run from the repo root:

    cd ~/RoArm

---

### 1. Circle / Helix Trajectory Demo

Script: `lessons/01_trajectory_and_gripper/circle_demo.py`

This demo:

- Torques the arm on.
- Moves to a known start pose using T=104.
- Streams a **circular or helical path** using T=1041:
  - (x, y) follow a circle.
  - z can be flat or sinusoidal (helix).
- Returns to a safe “candle” pose.
- Requests one T=105 feedback packet and prints XYZ.

Run:

    python3 lessons/01_trajectory_and_gripper/circle_demo.py

Key parameters inside the script:

- `R` – circle radius (mm).
- `REVOLUTIONS` – number of laps.
- `steps` – points per revolution (smoothness).
- `dt` – time between points (~trajectory frequency).
- `AMP` – vertical amplitude for helix (set `AMP = 0` for flat circle).

This script demonstrates:

- Streaming Cartesian commands at a steady rate.
- Understanding of the vendor’s T=104 / T=1041 interface.
- Safe return-to-home after the demo.

---

### 2. Line Trajectory Demo (if present)

Script: `lessons/01_trajectory_and_gripper/line_demo.py` (optional)

Similar to the circle demo but:

- Generates a **straight-line path** in task space between two XYZ points.
- Streams that path using T=1041.

Run:

    python3 lessons/01_trajectory_and_gripper/line_demo.py

This demonstrates joint-space / task-space thinking and simple path planning.

---

### 3. Gripper Tools

#### 3.1 High-level gripper control

Script: `lessons/01_trajectory_and_gripper/roarm_gripper.py`

Provides a small Python interface for the gripper:

- Converts desired “open/close” levels into the correct servo angle.
- Handles safety limit:
  - **Never command below ~1.2 rad** to avoid stalling.
- Can be imported by other scripts.

Usage pattern inside other scripts:

    from lessons/01_trajectory_and_gripper.roarm_gripper import set_gripper

    set_gripper(ser, angle_rad=2.8)  # nearly closed, but safe

#### 3.2 Gripper sweep / characterization

Script: `lessons/01_trajectory_and_gripper/gripper_sweep.py`

This utility:

- Sweeps the gripper through a set of angles.
- Lets you visually verify:
  - Which command values correspond to “open”, “pinched”, “almost stalled”.
- Confirms the mapping you measured (e.g. 1.2 rad ≈ 114°, 3.2 rad = fully closed).

Run:

    python3 lessons/01_trajectory_and_gripper/gripper_sweep.py

Safety:

- Keep fingers clear.
- Stop if the gripper obviously stalls or buzzes.

---

### Lesson 01 Takeaways

- You can stream **smooth task-space trajectories** to RoArm-M3 using the vendor’s IK.
- You understand T=104 (blocking move) vs T=1041 (streamed points).
- You created **reusable gripper utilities** with safety limits.
- You have a good interview story:

  “I implemented circle/line trajectory streaming and safe gripper control on a 6-DOF arm over UART using JSON T-codes.”
