Step 0 – Grab your calibration numbers

On the Pi, your planar_calib.json looks roughly like (numbers may differ slightly):

{
  "L1": 238.839,
  "L2": 316.731,
  "X0": -0.186,
  "Z0": -0.371,
  "shoulder_offset": 0.126072,
  "elbow_offset": -0.085031
}


For the hand calc, write these down:

L₁ = 238.839 mm

L₂ = 316.731 mm

X₀ = −0.186 mm

Z₀ = −0.371 mm

s₀ (shoulder_offset) = 0.126072 rad

e₀ (elbow_offset) = −0.085031 rad

Joint angles from IK (your test command):

b = 0

s = −0.473822 rad

e = 1.972540 rad

Step 1 – Compute effective angles for the planar chain

Your code does this (I’m just putting it into math symbols):

phi  = shoulder + shoulder_offset
eef  = elbow + elbow_offset   # "effective elbow"
phi2 = phi + eef


On paper:

Shoulder effective angle

𝜙 = 𝑠 + 𝑠₀

With numbers:

𝜙 = −0.473822 + 0.126072 = −0.347750 rad

Elbow effective angle

𝑒_eff = 𝑒 + 𝑒₀ = 1.972540 + (−0.085031) = 1.887509 rad

Angle of link 2

𝜙₂ = 𝜙 + 𝑒_eff = −0.347750 + 1.887509 = 1.539759 rad

So you now have:

φ ≈ −0.348 rad

φ₂ ≈ 1.540 rad

Step 2 – Compute sin and cos of those angles

Use a calculator (this is the “use your phone” step; no way I’d do this by hand):

sin(φ)

cos(φ)

sin(φ₂)

cos(φ₂)

For example (approx):

sin(−0.3478) ≈ −0.341

cos(−0.3478) ≈ +0.940

sin(1.5398) ≈ +0.999

cos(1.5398) ≈ +0.010

(Your calculator will give more precise values; that’s fine.)

Write them next to the angles on your paper.

Step 3 – Planar X–Z coordinates from L₁, L₂

The model (from your code) is:

x_p = L₁ sin(𝜙) + L₂ sin(𝜙₂) + X₀

z_p = L₁ cos(𝜙) + L₂ cos(𝜙₂) + Z₀


Now plug in step by step.

3.1 Compute link contributions in X

First link X:

x₁ = L₁ sin(𝜙) = 238.839 · sin(−0.347750)

Second link X:

x₂ = L₂ sin(𝜙₂) = 316.731 · sin(1.539759)

Sum with X₀:

x_p = x₁ + x₂ + X₀

Do those three numbers on your calculator. You should land very close to 235 mm.

3.2 Compute link contributions in Z

First link Z:

z₁ = L₁ cos(𝜙) = 238.839 · cos(−0.347750)

Second link Z:

z₂ = L₂ cos(𝜙₂) = 316.731 · cos(1.539759)

Sum with Z₀:

z_p = z₁ + z₂ + Z₀

Again, do the three numbers; you should land very close to 234 mm.

At this point you’ve reproduced what your script prints as:

Predicted FK (mm):
  x=235.000, y=0.000, z=234.000

Step 4 – Rotate by base (for general case)

For this test, base b = 0, so it’s trivial:

x = cos(b)·x_p = 1·x_p = x_p

y = sin(b)·x_p = 0·x_p = 0

z = z_p

So:

x ≈ 235 mm

y ≈ 0 mm

z ≈ 234 mm

If you picked a pose with non-zero base, you would use the same formulas with b ≠ 0 and get a non-zero y value.

Step 5 – Compare to firmware XYZ

Firmware feedback for your test pose is around:

"x": 237.1,
"y": 0.0,
"z": 229.9

So the difference between your planar FK model and the real arm is roughly:

Δx ≈ +2 mm

Δz ≈ −4 mm

|error| ≈ 4–5 mm

That’s exactly the ~4–5 mm you’re seeing in the logs.
The point of the paper FK is:

You’ve now reproduced the model by hand,

And you can see clearly the remaining gap is physical error / calibration residual, not math.

Recap as a quick checklist you can follow again

Copy L1, L2, X0, Z0, shoulder_offset, elbow_offset from planar_calib.json.

Copy b, s, e joint angles for a pose (e.g., from IK solution or firmware).

Compute:

φ = s + shoulder_offset

e_eff = e + elbow_offset

φ₂ = φ + e_eff

Compute sin and cos of φ and φ₂.

Compute:

x_p = L1·sin(φ) + L2·sin(φ₂) + X0

z_p = L1·cos(φ) + L2·cos(φ₂) + Z0

Rotate by base:

x = cos(b)·x_p

y = sin(b)·x_p

z = z_p

Compare (x,y,z) to firmware’s x,y,z.
\rmfamily
\end{document}
