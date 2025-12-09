#!/usr/bin/env python3
"""
roarm_simple_move.py

Minimal user-facing script for the Waveshare RoArm-M3-S.

Subcommands:
  - feedback : print current firmware feedback (T=105 -> T=1051)
  - home     : move to a tall-ish 'candle' pose (base=0, shoulder≈0, elbow≈0)
  - goto_xyz : move TCP to (x,y,z) using planar IK (+ optional simple refine)

Assumptions:
  - Firmware coordinate frame: origin at/near shoulder, X forward, Y left, Z up.
  - planar_calib.json exists and matches this arm, with keys:
      L1, L2, X0, Z0, shoulder_offset, elbow_offset
  - Communication is via USB serial (/dev/ttyUSB0, 115200 baud).
"""

import argparse
import json
import math
import os
import sys
import time

import serial

BAUD = 115200

# ---------------- Serial helpers ---------------- #

def open_serial(port: str, baud: int = BAUD, timeout: float = 1.0) -> serial.Serial:
    """Open serial port with RoArm-safe defaults."""
    s = serial.Serial(port=port, baudrate=baud, timeout=timeout, dsrdtr=None)
    s.setRTS(False)
    s.setDTR(False)
    time.sleep(0.2)
    return s


def send_json(s: serial.Serial, obj: dict) -> None:
    """Send one JSON object as a newline-terminated line."""
    line = json.dumps(obj, separators=(",", ":")) + "\n"
    s.write(line.encode("utf-8"))
    s.flush()


def read_feedback(s: serial.Serial, seconds: float = 1.2):
    """
    Send T=105 and return the last T=1051 dict within the time window.
    Returns None if nothing received.
    """
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


def torque_lock(s: serial.Serial, on: bool = True):
    """Enable or disable torque lock."""
    send_json(s, {"T": 210, "cmd": 1 if on else 0})
    time.sleep(0.15)


# ---------------- Kinematics (planar shoulder-origin + base yaw) ---------------- #

def load_calib(path: str | None):
    """
    Load planar calibration.
    Expected keys: L1, L2, X0, Z0, shoulder_offset, elbow_offset
    Falls back to conservative defaults if file missing.
    """
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
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return calib

    for k in calib.keys():
        if k in data:
            calib[k] = float(data[k])
    return calib


def fk_planar_xz(shoulder: float, elbow: float, calib: dict):
    """
    Model:
      phi  = shoulder + shoulder_offset   (angle from +Z, +phi rotates toward +X)
      eef  = elbow + elbow_offset         (relative elbow bend, 0 = straight)
      phi2 = phi + eef

      x = L1*sin(phi) + L2*sin(phi2) + X0
      z = L1*cos(phi) + L2*cos(phi2) + Z0
    """
    L1 = calib["L1"]
    L2 = calib["L2"]
    X0 = calib["X0"]
    Z0 = calib["Z0"]
    so = calib["shoulder_offset"]
    eo = calib["elbow_offset"]

    phi = shoulder + so
    eef = elbow + eo
    phi2 = phi + eef

    x = L1 * math.sin(phi) + L2 * math.sin(phi2) + X0
    z = L1 * math.cos(phi) + L2 * math.cos(phi2) + Z0
    return x, z


def fk_xyz(base: float, shoulder: float, elbow: float, calib: dict):
    """Forward kinematics in firmware XYZ frame using the planar model + base yaw."""
    xp, zp = fk_planar_xz(shoulder, elbow, calib)
    cb = math.cos(base)
    sb = math.sin(base)
    x = cb * xp
    y = sb * xp
    z = zp
    return x, y, z


def ik_xyz(x: float, y: float, z: float, calib: dict, elbow_sign: float = +1.0):
    """
    Solve for base, shoulder, elbow given target XYZ in firmware coords
    where origin is at shoulder, X forward, Y left, Z up.

    This matches your working roarm_fkik_uart.py kinematics:
      - Base yaw from atan2(y, x)
      - Planar 2-link solve in (xp,z) with offsets X0/Z0 and shoulder/elbow offsets.
    """
    L1 = calib["L1"]
    L2 = calib["L2"]
    X0 = calib["X0"]
    Z0 = calib["Z0"]
    so = calib["shoulder_offset"]
    eo = calib["elbow_offset"]

    # Base rotation
    base = math.atan2(y, x) if (abs(x) + abs(y)) > 1e-9 else 0.0

    # Planar radius from shoulder
    xp = math.hypot(x, y)

    # Shift by planar offsets
    xs = xp - X0
    zs = z - Z0

    r2 = xs * xs + zs * zs

    # Reachability / elbow angle
    denom = 2.0 * L1 * L2
    if denom <= 1e-9:
        raise ValueError("Bad calib: L1/L2 too small.")
    cos_e = (r2 - L1 * L1 - L2 * L2) / denom
    cos_e = max(-1.0, min(1.0, cos_e))

    eef = elbow_sign * math.acos(cos_e)  # relative elbow angle (0 straight)
    k1 = L1 + L2 * math.cos(eef)
    k2 = L2 * math.sin(eef)

    # phi: angle from +Z toward +X
    phi = math.atan2(xs, zs) - math.atan2(k2, k1)

    shoulder = phi - so
    elbow = eef - eo
    return base, shoulder, elbow


# ---------------- Motion helpers ---------------- #

def send_joints(
    s: serial.Serial,
    base: float,
    shoulder: float,
    elbow: float,
    wrist: float,
    roll: float,
    hand: float,
    spd: float = 0.0,
    acc: float = 10.0,
) -> None:
    """Send a T=102 multi-joint move in radians."""
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


# ---------------- Commands ---------------- #

def cmd_feedback(args):
    s = open_serial(args.port, args.baud, timeout=1.0)
    try:
        fb = read_feedback(s, seconds=1.2)
    finally:
        s.close()

    if not fb:
        print("[feedback] No T=1051 feedback received.")
    else:
        print(json.dumps(fb, indent=2))


def cmd_home(args):
    """
    Simple 'candle-ish' home using T=102:
      base=0, shoulder≈0, elbow≈0, wrist=0, roll=0, hand held near current value if possible.
    """
    s = open_serial(args.port, args.baud, timeout=1.0)

    try:
        # Get current gripper angle, so we don't surprise it
        fb0 = read_feedback(s, seconds=1.2)
        if fb0:
            current_g = float(fb0.get("g", 1.49))
        else:
            current_g = 1.49

        print("[home] Enabling torque and moving to tall 'candle' pose...")
        torque_lock(s, True)

        base = 0.0
        shoulder = 0.0
        elbow = 0.0
        wrist = 0.0
        roll = 0.0
        hand = current_g

        send_joints(s, base, shoulder, elbow, wrist, roll, hand, spd=0.0, acc=10.0)
        time.sleep(args.settle)

        fb = read_feedback(s, seconds=1.2)
        if fb:
            print("[home] Firmware feedback after move:")
            print(json.dumps(fb, indent=2))
        else:
            print("[home] No feedback after move.")
    finally:
        s.close()


def cmd_goto_xyz(args):
    # Resolve calib path
    calib_path = args.calib
    if calib_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        calib_path = os.path.join(script_dir, "planar_calib.json")

    calib = load_calib(calib_path)

    x_t = float(args.x)
    y_t = float(args.y)
    z_t = float(args.z)

    if z_t < args.zmin:
        print(
            f"[goto_xyz] ERROR: target z={z_t:.3f} mm is below safety minimum zmin={args.zmin:.3f} mm",
            file=sys.stderr,
        )
        sys.exit(1)

    s = open_serial(args.port, args.baud, timeout=1.0)

    try:
        # Capture current tool orientation and gripper
        fb0 = read_feedback(s, seconds=1.2)
        if fb0:
            current_t = float(fb0.get("t", 0.0))
            current_r = float(fb0.get("r", 0.0))
            current_g = float(fb0.get("g", 1.49))
        else:
            current_t = 0.0
            current_r = 0.0
            current_g = 1.49

        torque_lock(s, True)

        # Initial IK
        base, shoulder, elbow = ik_xyz(x_t, y_t, z_t, calib, elbow_sign=+1.0)
        fk_x, fk_y, fk_z = fk_xyz(base, shoulder, elbow, calib)

        print("IK solution (rad):")
        print(f"  base    = {base:.6f}")
        print(f"  shoulder= {shoulder:.6f}")
        print(f"  elbow   = {elbow:.6f}")
        print("Predicted FK (mm):")
        print(f"  x={fk_x:.3f}, y={fk_y:.3f}, z={fk_z:.3f}")

        # Send initial move
        send_joints(
            s,
            base,
            shoulder,
            elbow,
            wrist=current_t,
            roll=current_r,
            hand=current_g,
            spd=0.0,
            acc=10.0,
        )

        time.sleep(args.settle)
        fb = read_feedback(s, seconds=1.2)
        if not fb:
            print("[goto_xyz] No feedback after move.")
            return

        print("Firmware feedback after initial move:")
        print(json.dumps(fb, indent=2))

        # --- Initial error summary ---
        px = float(fb.get("x", 0.0))
        py = float(fb.get("y", 0.0))
        pz = float(fb.get("z", 0.0))
        err_x = x_t - px
        err_y = y_t - py
        err_z = z_t - pz
        err_norm = math.sqrt(err_x * err_x + err_y * err_y + err_z * err_z)
        print(
            f"Initial error: "
            f"ex={err_x:.3f}, ey={err_y:.3f}, ez={err_z:.3f}  |err|={err_norm:.3f} mm"
        )

        # Optional simple refine in XYZ space (no Jacobian)
        if args.refine and args.iters > 0:
            print("\nRefining using firmware feedback...")
            target = (x_t, y_t, z_t)
            current_fb = fb

            for i in range(1, args.iters + 1):
                px = float(current_fb.get("x", 0.0))
                py = float(current_fb.get("y", 0.0))
                pz = float(current_fb.get("z", 0.0))

                err_x = target[0] - px
                err_y = target[1] - py
                err_z = target[2] - pz
                err_norm = math.sqrt(err_x * err_x + err_y * err_y + err_z * err_z)

                print(
                    f"[refine {i}/{args.iters}] "
                    f"fb=({px:.3f},{py:.3f},{pz:.3f})  "
                    f"err=({err_x:.3f},{err_y:.3f},{err_z:.3f})  "
                    f"|err|={err_norm:.3f} mm"
                )

                if err_norm <= args.tol:
                    print(
                        f"[refine] Reached tolerance "
                        f"({err_norm:.3f} mm <= {args.tol:.3f} mm)."
                    )
                    break

                # Move partway toward target in XYZ
                adj_x = px + args.gain * err_x
                adj_y = py + args.gain * err_y
                adj_z = pz + args.gain * err_z

                if adj_z < args.zmin:
                    adj_z = args.zmin

                base, shoulder, elbow = ik_xyz(adj_x, adj_y, adj_z, calib, elbow_sign=+1.0)
                send_joints(
                    s,
                    base,
                    shoulder,
                    elbow,
                    wrist=current_t,
                    roll=current_r,
                    hand=current_g,
                    spd=0.0,
                    acc=10.0,
                )

                time.sleep(args.settle)
                next_fb = read_feedback(s, seconds=1.2)
                if not next_fb:
                    print("[refine] No feedback after refine step; stopping.")
                    break
                current_fb = next_fb

            # --- Final error summary after refine ---
            px = float(current_fb.get("x", 0.0))
            py = float(current_fb.get("y", 0.0))
            pz = float(current_fb.get("z", 0.0))
            err_x = x_t - px
            err_y = y_t - py
            err_z = z_t - pz
            err_norm = math.sqrt(err_x * err_x + err_y * err_y + err_z * err_z)

            print("\nFinal firmware feedback after refine:")
            print(json.dumps(current_fb, indent=2))
            print(
                f"Final error:   "
                f"ex={err_x:.3f}, ey={err_y:.3f}, ez={err_z:.3f}  |err|={err_norm:.3f} mm"
            )

    finally:
        s.close()


# ---------------- Argparse ---------------- #

def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Simple RoArm-M3-S control: home, feedback, goto_xyz"
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial port (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=BAUD,
        help="Baud rate (default: 115200)",
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # feedback
    p_fb = subparsers.add_parser("feedback", help="Query and print T=1051 feedback")
    p_fb.set_defaults(func=cmd_feedback)

    # home
    p_home = subparsers.add_parser("home", help="Move to a tall 'candle' home pose")
    p_home.add_argument(
        "--settle",
        type=float,
        default=6.0,
        help="Seconds to wait after home move before reading feedback (default: 6.0)",
    )
    p_home.set_defaults(func=cmd_home)

    # goto_xyz
    p_go = subparsers.add_parser(
        "goto_xyz", help="Move TCP to (x,y,z) in mm using planar IK"
    )
    p_go.add_argument("x", type=float, help="Target X in mm (firmware frame, shoulder-origin)")
    p_go.add_argument("y", type=float, help="Target Y in mm")
    p_go.add_argument("z", type=float, help="Target Z in mm")
    p_go.add_argument(
        "--calib",
        default=None,
        help="Path to planar_calib.json (default: ./planar_calib.json)",
    )
    p_go.add_argument(
        "--settle",
        type=float,
        default=5.0,
        help="Seconds to wait after each move before reading feedback (default: 5.0)",
    )
    p_go.add_argument(
        "--zmin",
        type=float,
        default=150.0,
        help="Safety minimum Z in mm (default: 150.0)",
    )
    p_go.add_argument(
        "--refine",
        action="store_true",
        help="Enable simple XYZ-space refine after initial IK move",
    )
    p_go.add_argument(
        "--iters",
        type=int,
        default=2,
        help="Number of refine iterations (default: 2)",
    )
    p_go.add_argument(
        "--gain",
        type=float,
        default=0.35,
        help="Refine gain (fraction of error to move toward per iteration, default: 0.35)",
    )
    p_go.add_argument(
        "--tol",
        type=float,
        default=2.0,
        help="Refine stop tolerance in mm (default: 2.0)",
    )

    p_go.set_defaults(func=cmd_goto_xyz)

    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
