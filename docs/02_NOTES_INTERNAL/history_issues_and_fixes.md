# History of Issues and Fixes

## Issue 1 – Wrong Origin (Base vs Shoulder)

**Symptom**  
FK/IK never matched firmware XYZ; large systematic errors.

**Root Cause**  
Assumed origin at the base instead of the **shoulder pitch** axis.

**Fix**  
Ran the shoulder sweep "circle test" and confirmed the end effector traced a circle centered at (0,0) in XZ.  
Rebuilt the model as shoulder-origin and fit `planar_calib.json`.

---

## Issue 2 – Wrong JSON Keys / T Codes

**Symptom**  
Robot jumped to presets or ignored commands.

**Root Cause**  
Used wrong JSON fields (`j1`, `j2`, etc.) or wrong `T` code instead of `T=102` with:

- `base`, `shoulder`, `elbow`, `wrist`, `roll`, `hand`

**Fix**  

- Standardized on `T=102` for multi-joint rad control.
- Added a `send_joints()` helper so all joint moves use firmware’s expected keys.

---

## Issue 3 – Serial / Torque Lock Weirdness

**Symptom**  
Commands sent but no movement; arm felt "locked".

**Root Cause**  

- RTS/DTR handshake on USB-UART causing odd behavior.
- Invalid commands leaving controller in a bad state until a valid move cleared it.

**Fix**  

- Open serial with `dsrdtr=None`, `setRTS(False)`, `setDTR(False)`, plus a short delay after opening.
- Send a known-good `T=102` to clear internal state.

---

## Issue 4 – Planar Model Mismatch

**Symptom**  
Even with shoulder-origin, IK was off by centimeters.

**Root Cause**  
Initial link lengths and offsets didn’t match the real arm.

**Fix**  

- Used safe sampling and planar fitting to solve for:
  `L1`, `L2`, `X0`, `Z0`, `shoulder_offset`, `elbow_offset`.
- Saved them as `planar_calib.json` and used that as the runtime model.

---

## Issue 5 – Old Refine Routines Diverging

**Symptom**  

- Error got worse each iteration.
- Arm drifted toward lower Z and risked table hits.

**Root Cause**  

- Aggressive joint updates without Z/X safety limits.
- Sampling too big a workspace without constraints.

**Fix**  

- Added `zmin` and x-limits for sampling and refine.
- Abort refine immediately if any limit is violated.

---

## Issue 6 – Simple Refine Has No Effect (Current)

**Symptom**  

- Target `(235, 0, 234)`:
  - Initial error ≈ 5.219 mm
  - After 2 refine iterations, error still ≈ 5.219 mm
- Firmware feedback identical.

**Root Cause**  

- Current refine uses the same planar model that already thinks the pose is perfect.  
  Error is model mismatch, not under-movement, so refine doesn’t change anything.

**Decision (for now)**  

- Document this refine as a **no-op** for accuracy.
- Accept ~5 mm error as the current baseline.
- Plan future Jacobian-based refinement that probes the real arm and updates joints from measured deltas.

---

## Issue 7 – Regression from Over-Editing Main Script

**Symptom**  

- Working states lost after heavy edits.
- Confusion over which file was the “real” runtime script.

**Root Cause**  
Experimenting directly in the main runtime file without a golden baseline.

**Fix**  

- Created `roarm_simple_move.py` as the **canonical runtime script**.
- Treat `roarm_simple_move.py` + `planar_calib.json` as **golden**:
  - No experiments directly in these files.
  - Copy to `roarm_experimental.py` (or similar) for new ideas.
