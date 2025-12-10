# Forward Kinematics (FK) — Manual Hand Calculation Guide  
_For Waveshare RoArm-M3S using shoulder-origin 2-link planar model + base yaw_

Last updated: 2025-12-09  
This document teaches YOU how to compute FK **by hand on paper**, matching the exact math inside `roarm_simple_move.py`.

---

# ============================================================
# 0. Inputs from planar_calib.json
# ============================================================

Example calibration:

```json
{
  "L1": 238.839,
  "L2": 316.731,
  "X0": -0.186,
  "Z0": -0.371,
  "shoulder_offset": 0.126072,
  "elbow_offset": -0.085031
}
```

Write these down:

- **L₁ = 238.839 mm**  
- **L₂ = 316.731 mm**  
- **X₀ = −0.186 mm**  
- **Z₀ = −0.371 mm**  
- **s₀ = 0.126072 rad** (shoulder_offset)  
- **e₀ = −0.085031 rad** (elbow_offset)

Joint angles (from IK or firmware):

- **b = 0.0 rad**  
- **s = −0.473822 rad**  
- **e = 1.972540 rad**

These are for the canonical test pose:

```
goto_xyz 235 0 234
```

---

# ============================================================
# 1. Compute effective angles
# ============================================================

The code does:

```
phi  = shoulder + shoulder_offset
eef  = elbow + elbow_offset
phi2 = phi + eef
```

### Shoulder effective angle
\[
\phi = s + s_0 = -0.473822 + 0.126072 = -0.347750 \text{ rad}
\]

### Elbow effective angle
\[
e_{eff} = e + e_0 = 1.972540 - 0.085031 = 1.887509 \text{ rad}
\]

### Link-2 angle
\[
\phi_2 = \phi + e_{eff} = -0.347750 + 1.887509 = 1.539759 \text{ rad}
\]

---

# ============================================================
# 2. Compute trig values
# ============================================================

Using a calculator:

| angle | sin() | cos() |
|-------|--------|--------|
| φ = −0.34775 | ≈ −0.341 | ≈ +0.940 |
| φ₂ = 1.539759 | ≈ +0.999 | ≈ +0.010 |

---

# ============================================================
# 3. Compute planar coordinates Xₚ, Zₚ
# ============================================================

Model:

\[
x_p = L_1\sin\phi + L_2\sin\phi_2 + X_0
\]

\[
z_p = L_1\cos\phi + L_2\cos\phi_2 + Z_0
\]

### 3.1 X-contributions

\[
x_1 = L_1\sin\phi \approx 238.839(-0.341)
\]

\[
x_2 = L_2\sin\phi_2 \approx 316.731(0.999)
\]

\[
x_p = x_1 + x_2 + X_0 \approx 235 \text{ mm}
\]

### 3.2 Z-contributions

\[
z_1 = L_1\cos\phi \approx 238.839(0.940)
\]

\[
z_2 = L_2\cos\phi_2 \approx 316.731(0.010)
\]

\[
z_p = z_1 + z_2 + Z_0 \approx 234 \text{ mm}
\]

---

# ============================================================
# 4. Apply base yaw rotation
# ============================================================

Base model:

```
x = cos(b)*x_p
y = sin(b)*x_p
z = z_p
```

Here **b = 0**, so:

- x = xₚ  
- y = 0  
- z = zₚ  

Final FK prediction:

\[
(x,y,z) \approx (235, 0, 234)
\]

---

# ============================================================
# 5. Compare to firmware feedback
# ============================================================

Firmware reported:

```
"x": 237.1,
"y": 0.0,
"z": 229.9
```

Error:

- Δx ≈ +2 mm  
- Δz ≈ −4 mm  
- |error| ≈ 4–5 mm (**expected**)

---

# RESULT

You can now compute FK for this arm **entirely on paper**.

For any pose:

1. Add offsets to shoulder & elbow  
2. Form φ and φ₂  
3. Compute sin, cos  
4. Compute xₚ, zₚ  
5. Rotate by base  
6. Compare to firmware  
7. Done.

---

# END OF FILE
