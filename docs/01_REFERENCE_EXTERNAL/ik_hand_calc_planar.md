# Inverse Kinematics (IK) — Manual Hand Calculation Guide  
_For Waveshare RoArm-M3S using shoulder-origin 2-link planar model + base yaw_

Last updated: 2025-12-09  
This document shows EXACTLY how to perform PLANAR IK by hand — no SciPy, no scripts.

Matches the IK inside `roarm_simple_move.py`.

---

# ============================================================
# 0. Inputs needed
# ============================================================

Target XYZ from the command:

```
goto_xyz 235 0 234
```

So:

\[
x = 235,\quad y = 0,\quad z = 234
\]

Calibration values (example):

- L₁ = 238.839 mm  
- L₂ = 316.731 mm  
- X₀ = −0.186 mm  
- Z₀ = −0.371 mm  
- s₀ = 0.126072 rad  
- e₀ = −0.085031 rad  

---

# ============================================================
# 1. Compute base angle
# ============================================================

Base yaw:

\[
b = \arctan2(y, x)
\]

Here:

\[
b = \arctan2(0, 235) = 0
\]

If y ≠ 0, you'll get a non-zero base angle.

Planar radius:

\[
x_p = \sqrt{x^2 + y^2} = 235
\]

---

# ============================================================
# 2. Shift the target to compensate for X₀, Z₀
# ============================================================

Firmware origin is **shoulder-origin**, but the calibration has small offsets:

\[
x_s = x_p - X_0 = 235 - (-0.186) = 235.186
\]

\[
z_s = z - Z_0 = 234 - (-0.371) = 234.371
\]

Distance in the shoulder-centered XZ plane:

\[
r^2 = x_s^2 + z_s^2
\]

---

# ============================================================
# 3. Solve the elbow angle (relative angle)
# ============================================================

Law of Cosines for a 2-link arm:

\[
\cos e_{eff} = \frac{r^2 - L_1^2 - L_2^2}{2 L_1 L_2}
\]

Clamp between ±1.

Solve:

\[
e_{eff} = \arccos(\cos e_{eff})
\]

Choose the **elbow-up** solution (positive) for our robot:

\[
e_{eff} \approx 1.8875 \text{ rad}
\]

Apply calibration offset:

\[
e = e_{eff} - e_0 = 1.887509 - (-0.085031) = 1.972540
\]

Matches your IK solution perfectly.

---

# ============================================================
# 4. Solve the shoulder angle
# ============================================================

We use:

\[
k_1 = L_1 + L_2\cos e_{eff}
\]
\[
k_2 = L_2\sin e_{eff}
\]

Pointing angle to target:

\[
\alpha = \arctan2(x_s, z_s)
\]

Relative geometry correction:

\[
\beta = \arctan2(k_2, k_1)
\]

Shoulder effective angle:

\[
\phi = \alpha - \beta
\]

Convert back to *firmware shoulder* by removing offset:

\[
s = \phi - s_0
\]

Plug in numbers → exactly:

\[
s = -0.473822 \text{ rad}
\]

---

# ============================================================
# 5. Final IK result
# ============================================================

\[
b = 0.000000
\]
\[
s = -0.473822
\]
\[
e = 1.972540
\]

This matches the script output PERFECTLY.

---

# ============================================================
# 6. FK Verification (optional)
# ============================================================

If you plug these into the FK document, you get:

\[
(235,\,0,\,234) \text{ mm}
\]

Which matches the target.

---

# RESULT

You now know how to compute IK for this arm:

1. Compute base angle  
2. Compute planar radius  
3. Shift by (X₀, Z₀)  
4. Solve elbow using Law of Cosines  
5. Solve shoulder using atan2 geometry  
6. Apply offsets  
7. Done  

This is EXACTLY the math inside your Python code.

---

# END OF FILE
