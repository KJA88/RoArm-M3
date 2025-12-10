Inverse Kinematics – 2-Link Planar + Rotating Base
(Calibration and target match the FK hand-calc sheet)

Step 0 – Grab your calibration numbers and target

From planar_calib.json:

L₁ = 238.839 mm
L₂ = 316.731 mm
X₀ = −0.186 mm
Z₀ = −0.371 mm
s₀ (shoulder_offset) = 0.126072 rad
e₀ (elbow_offset) = −0.085031 rad

Target position (firmware XYZ):

x = 235 mm
y = 0 mm
z = 234 mm

Goal: solve for joint angles

b = base
s = shoulder
e = elbow

such that the FK model lands at (x, y, z).

--------------------------------------------------
Step 1 – Base angle and planar radius

The base just rotates the arm around Z. First solve the yaw and the
planar radius in the X–Y plane.

Base angle:

b = atan2(y, x)

For x = 235, y = 0:

b = atan2(0, 235) = 0

Planar radius (distance from shoulder axis in the X–Y plane):

x_p = sqrt(x² + y²)

For x = 235, y = 0:

x_p = sqrt(235² + 0²) = 235

So in the arm’s vertical plane we now use:

x_p = 235 mm
z   = 234 mm

--------------------------------------------------
Step 2 – Undo the fitted origin offsets (X₀, Z₀)

The planar model uses tiny origin shifts X₀, Z₀. We convert the
target into the “pure” 2-link coordinates (x_s, z_s) seen by the
geometry:

x_s = x_p − X₀
z_s = z   − Z₀

With numbers:

x_s = 235 − (−0.186) = 235.186
z_s = 234 − (−0.371) = 234.371

So the ideal 2-link arm must reach:

(x_s, z_s) ≈ (235.186, 234.371)

--------------------------------------------------
Step 3 – Law of cosines to get the effective elbow angle e_eff

Now treat it as a standard 2-link arm:

link lengths L₁, L₂
end position (x_s, z_s)

First compute the distance r from shoulder to target:

r² = x_s² + z_s²
r  = sqrt(r²)

Then the law of cosines for the elbow bend:

cos(e_eff) = (r² − L₁² − L₂²) / (2 L₁ L₂)

Clamp cos(e_eff) to the range [−1, +1] if needed, then:

e_eff = ± arccos(cos(e_eff))

The sign (±) chooses the elbow “branch”:

+e_eff  → elbow-forward (your usual branch)
−e_eff  → elbow-backward

For this sheet we choose the forward-bending branch:

e_eff ≈ +1.887509 rad

(This matches what we used in the FK derivation.)

--------------------------------------------------
Step 4 – Compute shoulder effective angle φ

Define the helper terms:

k₁ = L₁ + L₂ cos(e_eff)
k₂ = L₂ sin(e_eff)

These represent the “combined link” from the shoulder to the target
in the rotated shoulder frame.

We also know the direction from the shoulder to the target:

θ = atan2(x_s, z_s)

(Note: atan2(x_s, z_s), not atan2(z_s, x_s), because φ is measured
from +Z toward +X.)

Then the shoulder effective angle is:

φ = θ − atan2(k₂, k₁)

With your numbers, this gives:

φ ≈ −0.347750 rad

So the geometry says:

φ ≈ −0.34775 rad
e_eff ≈ 1.88751  rad

--------------------------------------------------
Step 5 – Convert effective angles back to joint angles s and e

The planar model uses “effective” angles:

φ     = s + s₀
e_eff = e + e₀

So to get the firmware joint angles:

s = φ − s₀
e = e_eff − e₀

Plug in:

φ ≈ −0.347750
s₀ = 0.126072

e_eff ≈ 1.887509
e₀ = −0.085031

Shoulder:

s = −0.347750 − 0.126072
  ≈ −0.473822 rad

Elbow:

e = 1.887509 − (−0.085031)
  ≈ 1.972540 rad

Base (from Step 1):

b = 0

Final IK solution:

b ≈ 0.000000 rad
s ≈ −0.473822 rad
e ≈ 1.972540 rad

This matches the IK solution printed by the script.

--------------------------------------------------
Step 6 – Optional sanity check via FK

You can plug b, s, e back into the FK sheet:

1) Compute:
   φ     = s + s₀
   e_eff = e + e₀
   φ₂    = φ + e_eff

2) Compute x_p, z_p:
   x_p = L₁ sin(φ) + L₂ sin(φ₂) + X₀
   z_p = L₁ cos(φ) + L₂ cos(φ₂) + Z₀

3) Rotate by base:
   x = cos(b) · x_p
   y = sin(b) · x_p
   z = z_p

You should get approximately:
x ≈ 235 mm
y ≈ 0   mm
z ≈ 234 mm

--------------------------------------------------
Step 7 – IK checklist (reuse for any target)

Given L₁, L₂, X₀, Z₀, s₀, e₀ and target (x, y, z):

1) b   = atan2(y, x)
2) x_p = sqrt(x² + y²)
3) x_s = x_p − X₀
   z_s = z   − Z₀
4) r²     = x_s² + z_s²
   cos_e  = (r² − L₁² − L₂²) / (2 L₁ L₂)
   e_eff  = elbow_sign · arccos(clamp(cos_e))
5) k₁ = L₁ + L₂ cos(e_eff)
   k₂ = L₂ sin(e_eff)
   θ  = atan2(x_s, z_s)
   φ  = θ − atan2(k₂, k₁)
6) s = φ − s₀
   e = e_eff − e₀
7) Use (b, s, e) as your joint command or as the starting point for refine.
