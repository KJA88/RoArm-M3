# Runtime Planar Model (Shoulder-Origin IK)

## Coordinate System

- Origin: **Shoulder pitch axis** (not the base).
- Axes (firmware frame):
  - X: forward (in front of the arm)
  - Y: left (when facing the arm)
  - Z: up
- Units:
  - Position: millimeters (x, y, z)
  - Joints: radians

## Planar Calibration (`planar_calib.json`)

This file holds the calibrated 2-link shoulder–elbow model:

- `L1`, `L2`: effective link lengths (mm)
- `X0`, `Z0`: small origin offsets (mm)
- `shoulder_offset`, `elbow_offset`: joint zero offsets (rad)

Example values:

- L1 ≈ 238.839 mm  
- L2 ≈ 316.731 mm  
- X0 ≈ -0.186 mm  
- Z0 ≈ -0.371 mm  
- shoulder_offset ≈ 0.126 rad  
- elbow_offset ≈ -0.085 rad  

These come from fitting real firmware feedback (T=1051) while treating the origin as the shoulder pitch axis.

## Canonical Script: `roarm_simple_move.py`

This is the **simple, safe runtime CLI**.

Subcommands:

```bash
python3 roarm_simple_move.py feedback
python3 roarm_simple_move.py home
python3 roarm_simple_move.py goto_xyz X Y Z [--refine ...]
