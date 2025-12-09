#!/usr/bin/env python3
import argparse, csv, json, math
import numpy as np

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def predict(params, s, e):
    """
    Planar 2-link model in SHOULDER-origin firmware coords (XZ plane).
    rr = X0 + L1*sin(s+s0) + L2*sin(s+s0 + e+e0)
    z  = Z0 + L1*cos(s+s0) + L2*cos(s+s0 + e+e0)
    """
    L1, L2, X0, Z0, s0, e0 = params
    ss = s + s0
    ee = e + e0
    rr = X0 + L1*math.sin(ss) + L2*math.sin(ss + ee)
    z  = Z0 + L1*math.cos(ss) + L2*math.cos(ss + ee)
    return rr, z

def residuals(params, data):
    res = []
    for (rr_meas, z_meas, s, e) in data:
        rr_pred, z_pred = predict(params, s, e)
        res.append(rr_pred - rr_meas)
        res.append(z_pred - z_meas)
    return np.array(res, dtype=float)

def gauss_newton(data, p0, iters=60, lam=1e-3):
    p = np.array(p0, dtype=float)
    for _ in range(iters):
        r = residuals(p, data)
        # Numerical Jacobian
        J = np.zeros((len(r), len(p)), dtype=float)
        eps = 1e-5
        for j in range(len(p)):
            dp = np.zeros_like(p)
            dp[j] = eps
            r2 = residuals(p + dp, data)
            J[:, j] = (r2 - r) / eps

        A = J.T @ J + lam*np.eye(len(p))
        b = -(J.T @ r)
        try:
            dx = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            dx = np.linalg.lstsq(A, b, rcond=None)[0]

        p = p + dx

        # Keep it sane
        p[0] = clamp(p[0], 50.0, 600.0)    # L1
        p[1] = clamp(p[1], 50.0, 600.0)    # L2
        p[2] = clamp(p[2], -300.0, 300.0)  # X0
        p[3] = clamp(p[3], -300.0, 300.0)  # Z0
        p[4] = clamp(p[4], -1.5, 1.5)      # s0 (allow bigger)
        p[5] = clamp(p[5], -1.5, 1.5)      # e0 (allow bigger)

        if float(np.linalg.norm(dx)) < 1e-7:
            break

    final_r = residuals(p, data)
    final_rms = math.sqrt(float(np.mean(final_r*final_r)))
    return p, final_rms

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="samples_safe.csv")
    ap.add_argument("--out", default="planar_calib.json")
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--ymax", type=float, default=2.0, help="drop rows with |y| > ymax (mm)")
    args = ap.parse_args()

    data = []
    with open(args.csv_path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            x = float(row["x"])
            y = float(row["y"])
            z = float(row["z"])
            s = float(row["s_fb"])
            e = float(row["e_fb"])

            # Your sample set is base≈0 (y ~ 0), so planar coordinate is SIGNED rr = x
            if abs(y) > args.ymax:
                continue

            rr = x  # <-- critical fix (keeps negative x)

            data.append((rr, z, s, e))

    if len(data) < 10:
        raise SystemExit(f"Not enough usable rows after filtering (got {len(data)}).")

    # Good initial guess based on your real arm
    p0 = [236.0, 320.0, 55.0, 0.0, 0.0, 0.0]

    p, rms = gauss_newton(data, p0, iters=args.iters, lam=1e-3)

    L1, L2, X0, Z0, s0, e0 = [float(v) for v in p]
    out = {
        "L1": L1,
        "L2": L2,
        "X0": X0,
        "Z0": Z0,
        "shoulder_offset": s0,
        "elbow_offset": e0
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    print("\n=== PLANAR FIT RESULT (shoulder-origin) ===")
    print(f"rows used: {len(data)}")
    print(f"RMS position error (X,Z): {rms:.3f} mm")
    print(f"L1 = {L1:.3f} mm")
    print(f"L2 = {L2:.3f} mm")
    print(f"X0 = {X0:.3f} mm")
    print(f"Z0 = {Z0:.3f} mm")
    print(f"shoulder_offset = {s0:.6f} rad")
    print(f"elbow_offset    = {e0:.6f} rad")
    print(f"\nWrote: {args.out}")

if __name__ == "__main__":
    main()
