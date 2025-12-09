#!/usr/bin/env python3
import argparse, json, math, sys, time
import serial

BAUD = 115200

# ---------------- Serial helpers ----------------
def open_serial(port: str):
    s = serial.Serial(port, baudrate=BAUD, timeout=1, dsrdtr=None)
    s.setRTS(False)
    s.setDTR(False)
    time.sleep(0.2)
    return s

def send_json(s, obj):
    s.write((json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8"))

def read_feedback(s, seconds=1.2):
    """Send T=105 and return last T=1051 dict within window."""
    send_json(s, {"T": 105})
    end = time.time() + seconds
    last = None
    while time.time() < end:
        raw = s.readline()
        if not raw:
            continue
        txt = raw.decode("utf-8", errors="ignore").strip()
        if not txt.startswith("{"):
            continue
        try:
            msg = json.loads(txt)
        except Exception:
            continue
        if isinstance(msg, dict) and msg.get("T") == 1051:
            last = msg
    return last

def torque_lock(s, on=True):
    send_json(s, {"T": 210, "cmd": 1 if on else 0})
    time.sleep(0.15)

# ---------------- Kinematics (planar shoulder-origin + base yaw) ----------------
def load_calib(path):
    # Defaults are conservative-ish; your planar_calib.json should override.
    calib = {
        "L1": 238.0,
        "L2": 316.0,
        "X0": 0.0,
        "Z0": 0.0,
        "shoulder_offset": 0.0,
        "elbow_offset": 0.0,
    }
    if not path:
        return calib
    with open(path, "r") as f:
        data = json.load(f)
    # Support a few possible key styles
    for k in ("L1","L2","X0","Z0","shoulder_offset","elbow_offset"):
        if k in data:
            calib[k] = float(data[k])
    return calib

def fk_planar_xz(shoulder, elbow, calib):
    """
    Model:
      phi  = shoulder + shoulder_offset   (angle from +Z, +phi rotates toward +X)
      phi2 = phi + (elbow + elbow_offset) (relative elbow bend, 0 = straight)
      x = L1*sin(phi) + L2*sin(phi2) + X0
      z = L1*cos(phi) + L2*cos(phi2) + Z0
    """
    L1 = calib["L1"]; L2 = calib["L2"]
    X0 = calib["X0"]; Z0 = calib["Z0"]
    so = calib["shoulder_offset"]; eo = calib["elbow_offset"]

    phi  = shoulder + so
    eef  = elbow + eo
    phi2 = phi + eef

    x = L1 * math.sin(phi) + L2 * math.sin(phi2) + X0
    z = L1 * math.cos(phi) + L2 * math.cos(phi2) + Z0
    return x, z

def fk_xyz(base, shoulder, elbow, calib):
    xp, zp = fk_planar_xz(shoulder, elbow, calib)
    cb = math.cos(base)
    sb = math.sin(base)
    x = cb * xp
    y = sb * xp
    z = zp
    return x, y, z

def ik_xyz(x, y, z, calib, elbow_sign=+1):
    """
    Solve for base, shoulder, elbow given target XYZ in firmware coords
    where origin is at shoulder, X forward, Y left, Z up.
    """
    L1 = calib["L1"]; L2 = calib["L2"]
    X0 = calib["X0"]; Z0 = calib["Z0"]
    so = calib["shoulder_offset"]; eo = calib["elbow_offset"]

    base = math.atan2(y, x) if (abs(x) + abs(y)) > 1e-9 else 0.0
    xp = math.hypot(x, y)

    # shift by fitted origin offsets
    xs = xp - X0
    zs = z  - Z0

    r2 = xs*xs + zs*zs
    r = math.sqrt(r2)

    # Reachability clamp
    denom = 2.0 * L1 * L2
    if denom <= 1e-9:
        raise ValueError("Bad calib: L1/L2 too small.")
    cos_e = (r2 - L1*L1 - L2*L2) / denom
    cos_e = max(-1.0, min(1.0, cos_e))

    eef = elbow_sign * math.acos(cos_e)  # relative elbow (0 straight, + bends)
    k1 = L1 + L2 * math.cos(eef)
    k2 = L2 * math.sin(eef)

    # angle from +Z toward +X
    phi = math.atan2(xs, zs) - math.atan2(k2, k1)

    shoulder = phi - so
    elbow    = eef - eo
    return base, shoulder, elbow

# ---------------- Motion command ----------------
def send_joints(s, base, shoulder, elbow, wrist, roll, hand, spd, acc):
    cmd = {
        "T": 102,
        "base": float(base),
        "shoulder": float(shoulder),
        "elbow": float(elbow),
        "wrist": float(wrist),
        "roll": float(roll),
        "hand": float(hand),
        "spd": float(spd),
        "acc": int(acc),
    }
    send_json(s, cmd)

def safe_ok(x, z, zmin, xmin, xmax):
    return (z >= zmin) and (xmin <= x <= xmax)

# ---------------- Refine using firmware feedback ----------------
def refine_to_target(s, target_xyz, base, shoulder, elbow, wrist, roll, hand,
                     spd, acc, iters, probe, gain, settle, zmin, xmin, xmax):
    """
    Closed-loop refine in XZ (and base for Y) using finite-diff Jacobian from firmware.
    Keeps wrist/roll/hand fixed.
    """
    tx, ty, tz = target_xyz

    def do_move(b, sh, el):
        send_joints(s, b, sh, el, wrist, roll, hand, spd, acc)
        time.sleep(settle)
        fb = read_feedback(s, seconds=1.2)
        if not fb:
            raise RuntimeError("No feedback (T=1051).")
        return fb

    # Start at provided angles
    fb = do_move(base, shoulder, elbow)

    for i in range(iters):
        fx, fy, fz = float(fb["x"]), float(fb["y"]), float(fb["z"])

        # Safety guard on current pose
        if not safe_ok(fx, fz, zmin, xmin, xmax):
            print(f"[refine {i+1}/{iters}] ABORT safety: fb x={fx:.1f} z={fz:.1f}")
            break

        ex = (tx - fx)
        ey = (ty - fy)
        ez = (tz - fz)
        err = math.sqrt(ex*ex + ey*ey + ez*ez)
        print(f"[refine {i+1}/{iters}] fb=({fx:.3f},{fy:.3f},{fz:.3f})  "
              f"err=({ex:.3f},{ey:.3f},{ez:.3f})  |err|={err:.3f} mm")

        # If close enough, stop
        if err <= 2.0:
            break

        # Build a simple Jacobian for (x,z) wrt (shoulder, elbow)
        # probe shoulder
        fb_sp = do_move(base, shoulder + probe, elbow)
        fb_sm = do_move(base, shoulder - probe, elbow)
        dxdsh = (float(fb_sp["x"]) - float(fb_sm["x"])) / (2.0 * probe)
        dzdsh = (float(fb_sp["z"]) - float(fb_sm["z"])) / (2.0 * probe)

        # probe elbow
        fb_ep = do_move(base, shoulder, elbow + probe)
        fb_em = do_move(base, shoulder, elbow - probe)
        dxdel = (float(fb_ep["x"]) - float(fb_em["x"])) / (2.0 * probe)
        dzdel = (float(fb_ep["z"]) - float(fb_em["z"])) / (2.0 * probe)

        # Solve 2x2: [dxdsh dxdel; dzdsh dzdel] * [dsh; del] = [ex; ez]
        det = dxdsh * dzdel - dxdel * dzdsh
        if abs(det) < 1e-6:
            print("Jacobian near-singular; stopping refine.")
            break

        dsh = ( ex * dzdel - dxdel * ez) / det
        del_ = (-ex * dzdsh + dxdsh * ez) / det

        shoulder += gain * dsh
        elbow    += gain * del_

        # Optionally adjust base from Y error (small-angle approx)
        # If ty!=0 and we are off in y, nudge base slightly
        if abs(tx) + abs(ty) > 1e-6 and abs(ey) > 0.5:
            # approximate: y ≈ xp*sin(base). If base small, sin(base)≈base.
            # Use feedback x as xp proxy when base is small.
            xp = math.hypot(fx, fy)
            if xp > 1e-6:
                base += gain * (ey / xp)

        fb = do_move(base, shoulder, elbow)

    return base, shoulder, elbow, fb

# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--calib", default=None, help="planar_calib.json from roarm_fit_planar.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("feedback")

    p_home = sub.add_parser("home")
    p_home.add_argument("--spd", type=float, default=0.6)
    p_home.add_argument("--acc", type=int, default=10)

    p_candle = sub.add_parser("candle")
    p_candle.add_argument("--spd", type=float, default=0.6)
    p_candle.add_argument("--acc", type=int, default=10)
    p_candle.add_argument("--hand", type=float, default=1.5, help="safe default (avoid <1.1)")

    p_fk = sub.add_parser("fk")
    p_fk.add_argument("base", type=float)
    p_fk.add_argument("shoulder", type=float)
    p_fk.add_argument("elbow", type=float)

    p_ik = sub.add_parser("ik")
    p_ik.add_argument("x", type=float)
    p_ik.add_argument("y", type=float)
    p_ik.add_argument("z", type=float)
    p_ik.add_argument("--send", action="store_true")
    p_ik.add_argument("--prefer-current", action="store_true")
    p_ik.add_argument("--spd", type=float, default=0.6)
    p_ik.add_argument("--acc", type=int, default=10)

    # SAFE refine (firmware feedback)
    p_ik.add_argument("--refine", action="store_true")
    p_ik.add_argument("--iters", type=int, default=4)
    p_ik.add_argument("--probe", type=float, default=0.010)
    p_ik.add_argument("--gain", type=float, default=0.6)
    p_ik.add_argument("--settle", type=float, default=1.2)

    # Safety limits for refine / sends
    p_ik.add_argument("--zmin", type=float, default=150.0)
    p_ik.add_argument("--xmin", type=float, default=-220.0)
    p_ik.add_argument("--xmax", type=float, default=560.0)

    args = ap.parse_args()
    calib = load_calib(args.calib)

    if args.cmd == "fk":
        x, y, z = fk_xyz(args.base, args.shoulder, args.elbow, calib)
        print(f"x={x:.3f} mm, y={y:.3f} mm, z={z:.3f} mm")
        return

    s = open_serial(args.port)
    try:
        torque_lock(s, True)

        if args.cmd == "feedback":
            fb = read_feedback(s, seconds=1.2)
            if not fb:
                print("No feedback.")
                return
            print(json.dumps(fb, indent=2))
            return

        if args.cmd == "home":
            # Move init
            send_json(s, {"T": 100})
            time.sleep(2.0)
            fb = read_feedback(s, seconds=1.2)
            if fb:
                print(json.dumps(fb, indent=2))
            return

        if args.cmd == "candle":
            # Candle = base/shoulder/elbow/wrist/roll to 0, hand to safe value
            send_joints(s, 0.0, 0.0, 0.0, 0.0, 0.0, float(args.hand), args.spd, args.acc)
            time.sleep(1.2)
            fb = read_feedback(s, seconds=1.2)
            if fb:
                print(json.dumps(fb, indent=2))
            return

        if args.cmd == "ik":
            base, shoulder, elbow = ik_xyz(args.x, args.y, args.z, calib, elbow_sign=+1)
            px, py, pz = fk_xyz(base, shoulder, elbow, calib)

            print("IK solution (rad):")
            print(f"  base    = {base:.6f}")
            print(f"  shoulder= {shoulder:.6f}")
            print(f"  elbow   = {elbow:.6f}")
            print("Predicted FK (mm):")
            print(f"  x={px:.3f}, y={py:.3f}, z={pz:.3f}")

            if not args.send:
                return

            # Decide what wrist/roll/hand to send
            wrist = 0.0
            roll  = 0.0
            hand  = 1.5

            if args.prefer_current:
                fb0 = read_feedback(s, seconds=1.2)
                if not fb0:
                    raise RuntimeError("No feedback to prefer-current from.")
                wrist = float(fb0.get("t", 0.0))
                roll  = float(fb0.get("r", 0.0))
                hand  = float(fb0.get("g", 1.5))

            # Basic safety check (target itself)
            if not safe_ok(args.x, args.z, args.zmin, args.xmin, args.xmax):
                print(f"ABORT (safety): target x={args.x:.1f} z={args.z:.1f} violates limits.")
                return

            # Move once
            send_joints(s, base, shoulder, elbow, wrist, roll, hand, args.spd, args.acc)
            time.sleep(args.settle)

            fb = read_feedback(s, seconds=1.2)
            if fb:
                print("Firmware feedback:")
                print(json.dumps(fb, indent=2))

            # Optional closed-loop refine
            if args.refine:
                print("\nRefining using firmware feedback...")
                base2, sh2, el2, fb2 = refine_to_target(
                    s,
                    (args.x, args.y, args.z),
                    base, shoulder, elbow,
                    wrist, roll, hand,
                    args.spd, args.acc,
                    args.iters, args.probe, args.gain, args.settle,
                    args.zmin, args.xmin, args.xmax
                )
                print("\nFinal joints (rad):")
                print(f"  base    = {base2:.6f}")
                print(f"  shoulder= {sh2:.6f}")
                print(f"  elbow   = {el2:.6f}")
                print("Firmware feedback:")
                print(json.dumps(fb2, indent=2))

            return

    finally:
        s.close()

if __name__ == "__main__":
    main()
