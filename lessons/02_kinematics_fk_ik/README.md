## Lesson 02 – Planar FK/IK Model & Consistency Test

**Intent**

This lesson shows that you can:

- Build a **calibrated planar kinematic model** of the arm (shoulder-origin).
- Implement **forward kinematics (FK)** and **inverse kinematics (IK)** in Python.
- Validate FK/IK numerically with a **consistency test harness**.
- Use IK to command real robot motions.

This is your “I actually understand and implement kinematics, not just call the firmware” lesson.

All commands run from repo root:

    cd ~/RoArm

---

### 1. Planar Model & Calibration

The planar model uses parameters from:

- `planar_calib.json`:
  - `L1` – shoulder → elbow length
  - `L2` – elbow → wrist length
  - `X0, Z0` – rigid translation offsets
  - `shoulder_offset`
  - `elbow_offset`

These are obtained by:

    python3 roarm_collect_samples_safe.py
    python3 roarm_fit_planar.py

> **Never hand-edit** `planar_calib.json`.  
> Always regenerate it via the calibration pipeline.

---

### 2. Runtime Kinematics Model

Effective joint angles:

- `φ    = shoulder + shoulder_offset`
- `e_eff = elbow + elbow_offset`
- `φ₂   = φ + e_eff`

Planar FK (in shoulder frame):

- `x_p = L1*sin(φ) + L2*sin(φ₂) + X0`
- `z_p = L1*cos(φ) + L2*cos(φ₂) + Z0`

Base rotation:

- `x = cos(base) * x_p`
- `y = sin(base) * x_p`
- `z = z_p`

Inverse kinematics (planar):

- `base = atan2(y, x)`
- `x_p  = hypot(x, y)`
- Solve triangle via law of cosines to get `e_eff`
- Solve geometry for `φ`
- Recover servo-space joint angles:
  - `shoulder = φ    - shoulder_offset`
  - `elbow    = e_eff - elbow_offset`

These equations are implemented exactly the same way in the Python code and documented under `/docs`.

---

### 3. FK/IK Consistency Test Harness

Script: `lessons/02_kinematics_fk_ik/test_fk_ik_consistency.py`

This script:

1. Loads the calibrated planar parameters from `planar_calib.json`.
2. Samples many joint combinations `(base, shoulder, elbow)` within safe limits.
3. For each sample:
   - Uses **FK** to compute `(x, z)` (planar).
   - Calls **IK** on that `(x, z)` to get back `(shoulder', elbow')`.
   - Runs FK again and measures the position error.
4. Prints statistics like:

       [0] pos_err = 0.416 mm
       [50] pos_err = 0.416 mm
       ...
       === FK/IK Consistency Summary ===
       Total samples: 300
       IK failures : 1
       Successful samples: 299
       Position error (mm):
         mean = 0.416
         max  = 0.416

Run:

    python3 lessons/02_kinematics_fk_ik/test_fk_ik_consistency.py

Notes:

- This script is **purely offline**:
  - It does **not** open the serial port.
  - It does **not** move the robot.
  - It does **not** overwrite any calibration files.
- It is safe to run anytime; it just tests the math.

---

### 4. Using IK to Move the Real Arm

Script: `roarm_simple_move.py` (at repo root)

This script integrates your planar IK with the actual robot:

- `home` move – send arm to a known safe pose.
- `goto_xyz X Y Z` – compute base/shoulder/elbow from (X, Y, Z) using T=102:

      python3 roarm_simple_move.py goto_xyz 235 0 234

- Uses the correct JSON keys:

  - `{"T":102,"base":...,"shoulder":...,"elbow":...,"wrist":...,"roll":...,"hand":...}`

This shows you can **bridge your own kinematics math to real hardware.**

---

### Lesson 02 Takeaways

- You have a **calibrated planar kinematic model** of the arm.
- You implemented and tested **FK and IK** with ~0.4 mm internal error.
- You wrote a **consistency harness** to validate the math.
- You used IK to drive a real robot to target XYZ poses using T=102.
- This is strong evidence that you can do real robotics kinematics work.
