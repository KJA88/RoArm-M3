#!/usr/bin/env python3
"""
FK/IK consistency test harness for the RoArm planar model.

- Loads planar_calib.json (L1, L2, X0, Z0, shoulder_offset, elbow_offset)
- Defines planar FK and IK using the same equations as docs/runtime_planar_model.md
- Randomly samples joint angles (base, shoulder, elbow)
- Runs FK -> IK -> FK and measures position error in mm

Run:
    python3 test_fk_ik_consistency.py
"""

import json
import math
import random
from pathlib import Path
from statistics import mean

# ---------------------------------------------------------------------
# 1) Load calibration parameters from planar_calib.json
# ---------------------------------------------------------------------

CALIB_PATH = Path("planar_calib.json")

if not CALIB_PATH.exists():
    raise FileNotFoundError("planar_calib.json not found in repo root.")

calib = json.loads(CALIB_PATH.read_text())

# Expected keys: L1, L2, X0, Z0, shoulder_offset, elbow_offset
L1 = calib["L1"]
L2 = calib["L2"]
X0 = calib["X0"]
Z0 = calib["Z0"]
SHOULDER_OFFSET = calib["shoulder_offset"]
ELBOW_OFFSET = calib["elbow_offset"]


# ---------------------------------------------------------------------
# 2) Planar FK: from (base, shoulder, elbow) -> (x, y, z)
#    Shoulder-origin, calibrated with offsets.
# ---------------------------------------------------------------------

def fk_planar(base: float, shoulder: float, elbow: float):
    """
    FK for the 2-link planar model with base rotation.

    Effective angles:
        φ     = shoulder + shoulder_offset
        e_eff = elbow    + elbow_offset
        φ2    = φ + e_eff

    Planar:
        x_p = L1*sin(φ) + L2*sin(φ2) + X0
        z_p = L1*cos(φ) + L2*cos(φ2) + Z0

    Base rotation:
        x = cos(base) * x_p
        y = sin(base) * x_p
        z = z_p

    Returns:
        (x, y, z) in mm in the firmware shoulder frame.
    """
    phi = shoulder + SHOULDER_OFFSET
    e_eff = elbow + ELBOW_OFFSET
    phi2 = phi + e_eff

    x_p = L1 * math.sin(phi) + L2 * math.sin(phi2) + X0
    z_p = L1 * math.cos(phi) + L2 * math.cos(phi2) + Z0

    cb = math.cos(base)
    sb = math.sin(base)

    x = cb * x_p
    y = sb * x_p
    z = z_p

    return x, y, z


# ---------------------------------------------------------------------
# 3) Planar IK: from (x, y, z) -> (base, shoulder, elbow)
#    Using triangle geometry / law of cosines.
# ---------------------------------------------------------------------

def ik_planar(x: float, y: float, z: float):
    """
    Inverse kinematics for the calibrated 2-link planar model.

    Steps:
        base = atan2(y, x)
        x_p  = hypot(x, y)

        r^2 = x_p^2 + z^2

        cos(e_eff) = (r^2 - L1^2 - L2^2) / (2 * L1 * L2)
        e_eff      = acos(...)
        φ          = atan2(x_p, z) - atan2(L2*sin(e_eff), L1 + L2*cos(e_eff))

        shoulder = φ     - shoulder_offset
        elbow    = e_eff - elbow_offset

    Returns:
        (base, shoulder, elbow, ok_flag)
    """
    base = math.atan2(y, x)
    x_p = math.hypot(x, y)

    # distance from shoulder to wrist in the planar (x_p, z) plane
    r2 = x_p * x_p + z * z

    # Law of cosines for e_eff
    denom = 2.0 * L1 * L2
    cos_e = (r2 - L1 * L1 - L2 * L2) / denom

    # Numerical safety clamp to [-1, 1]
    if cos_e < -1.0 or cos_e > 1.0:
        # Outside reach
        return 0.0, 0.0, 0.0, False

    cos_e = max(-1.0, min(1.0, cos_e))
    e_eff = math.acos(cos_e)

    # Geometry for φ
    # "Shoulder angle" to the wrist point, minus the triangle offset
    # atan2(L2*sin(e_eff), L1 + L2*cos(e_eff)) is the "elbow contribution"
    phi_center = math.atan2(x_p, z)
    phi_offset = math.atan2(L2 * math.sin(e_eff), L1 + L2 * math.cos(e_eff))
    phi = phi_center - phi_offset

    shoulder = phi - SHOULDER_OFFSET
    elbow = e_eff - ELBOW_OFFSET

    return base, shoulder, elbow, True


# ---------------------------------------------------------------------
# 4) Sampling and consistency test
# ---------------------------------------------------------------------

def sample_joint():
    """
    Sample a safe-ish triple (base, shoulder, elbow).

    These ranges are approximate and should be tuned to your real workspace.
    """
    base = random.uniform(-1.2, 1.2)       # rad
    shoulder = random.uniform(-0.2, 2.2)   # rad
    elbow = random.uniform(-1.2, 1.2)      # rad
    return base, shoulder, elbow


def main():
    N = 300  # number of random tests

    pos_errors = []
    bad_ik = 0

    for i in range(N):
        b0, s0, e0 = sample_joint()

        # FK -> (x0, y0, z0)
        x0, y0, z0 = fk_planar(b0, s0, e0)

        # IK -> (b1, s1, e1, ok)
        b1, s1, e1, ok = ik_planar(x0, y0, z0)
        if not ok:
            bad_ik += 1
            continue

        # FK again from IK result
        x1, y1, z1 = fk_planar(b1, s1, e1)

        dx = x1 - x0
        dy = y1 - y0
        dz = z1 - z0
        pos_err = math.sqrt(dx * dx + dy * dy + dz * dz)

        pos_errors.append(pos_err)

        if i % 50 == 0:
            print(f"[{i}] pos_err = {pos_err:.3f} mm")

    print("\n=== FK/IK Consistency Summary ===")
    print(f"Total samples: {N}")
    print(f"IK failures : {bad_ik}")

    if not pos_errors:
        print("No successful IK samples.")
        return

    print(f"Successful samples: {len(pos_errors)}")
    print(f"Position error (mm):")
    print(f"  mean = {mean(pos_errors):.3f}")
    print(f"  max  = {max(pos_errors):.3f}")


if __name__ == "__main__":
    main()
