#!/usr/bin/env python3
import csv, time, json, argparse, math
import serial

BAUD=115200

def open_serial(port):
    s = serial.Serial(port, baudrate=BAUD, timeout=1, dsrdtr=None)
    s.setRTS(False); s.setDTR(False)
    time.sleep(0.2)
    return s

def send_json(s, obj):
    s.write((json.dumps(obj,separators=(",",":"))+"\n").encode("utf-8"))

def torque_lock(s, on=True):
    send_json(s, {"T":210, "cmd": 1 if on else 0})
    time.sleep(0.15)

def get_feedback(s, wait=1.2):
    send_json(s, {"T":105})
    end=time.time()+wait
    last=None
    while time.time()<end:
        raw=s.readline()
        if not raw: continue
        txt=raw.decode("utf-8", errors="ignore").strip()
        if not txt.startswith("{"): continue
        try:
            msg=json.loads(txt)
        except:
            continue
        if msg.get("T")==1051:
            last=msg
    return last

def send_joints(s, base, shoulder, elbow, wrist=0.0, roll=0.0, hand=3.129320807, spd=0.35, acc=0):
    send_json(s, {
        "T":102,
        "base":float(base),
        "shoulder":float(shoulder),
        "elbow":float(elbow),
        "wrist":float(wrist),
        "roll":float(roll),
        "hand":float(hand),
        "spd":float(spd),
        "acc":int(acc)
    })

def guarded_move(s, target_base, target_sh, target_el, spd, zmin, xmin, xmax, steps=10):
    """
    Move in small steps and ABORT if firmware feedback enters forbidden region.
    Returns (ok, last_feedback).
    """
    fb0 = get_feedback(s, wait=0.8)
    if not fb0:
        return False, None

    b0 = float(fb0.get("b", 0.0))
    s0 = float(fb0.get("s", 0.0))
    e0 = float(fb0.get("e", 0.0))

    for k in range(1, steps+1):
        u = k/steps
        b = b0 + u*(target_base - b0)
        sh= s0 + u*(target_sh   - s0)
        el= e0 + u*(target_el   - e0)

        send_joints(s, b, sh, el, spd=spd)
        time.sleep(0.45)

        fb = get_feedback(s, wait=0.6)
        if not fb:
            return False, None

        x=float(fb["x"]); z=float(fb["z"])
        if (z < zmin) or (x < xmin) or (x > xmax):
            # Stop immediately: go back to candle-ish (safe) using current base
            send_joints(s, float(fb.get("b",0.0)), 0.0, 0.0, spd=0.6)
            time.sleep(0.8)
            return False, fb

    return True, fb

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--out", default="samples_safe.csv")
    ap.add_argument("--spd", type=float, default=0.35)

    # Safety box in firmware coords (shoulder-origin)
    ap.add_argument("--zmin", type=float, default=120.0)
    ap.add_argument("--xmin", type=float, default=-220.0)
    ap.add_argument("--xmax", type=float, default=560.0)

    args=ap.parse_args()

    # Safer starting grid (still plenty of coverage)
    shoulders = [-0.6, -0.3, 0.0, 0.3, 0.6]
    elbows    = [0.3, 0.6, 1.0, 1.4, 1.8]

    s=open_serial(args.port)
    torque_lock(s, True)

    with open(args.out, "w", newline="") as f:
        w=csv.writer(f)
        w.writerow([
            "t_unix","base_cmd","shoulder_cmd","elbow_cmd",
            "x","y","z","tit","b_fb","s_fb","e_fb","t_fb","r_fb","g_fb"
        ])

        # Start from candle-ish
        send_joints(s, 0.0, 0.0, 0.0, spd=0.6)
        time.sleep(0.9)
        fb=get_feedback(s)
        if fb:
            w.writerow([time.time(),0.0,0.0,0.0, fb["x"],fb["y"],fb["z"],fb["tit"], fb["b"],fb["s"],fb["e"],fb["t"],fb["r"],fb["g"]])
            f.flush()

        for sh in shoulders:
            for el in elbows:
                print(f"cmd sh={sh:.3f} el={el:.3f}")
                ok, fb = guarded_move(s, 0.0, sh, el, spd=args.spd,
                                      zmin=args.zmin, xmin=args.xmin, xmax=args.xmax,
                                      steps=10)
                if not ok:
                    if fb:
                        print(f"  ABORTED (safety): x={fb['x']:.1f} z={fb['z']:.1f}  (limits: z>={args.zmin}, {args.xmin}<=x<={args.xmax})")
                    else:
                        print("  ABORTED (no feedback)")
                    continue

                w.writerow([time.time(),0.0,sh,el, fb["x"],fb["y"],fb["z"],fb["tit"], fb["b"],fb["s"],fb["e"],fb["t"],fb["r"],fb["g"]])
                f.flush()
                print(f"  fb x={fb['x']:.3f} y={fb['y']:.3f} z={fb['z']:.3f}   s={fb['s']:.6f} e={fb['e']:.6f}")

    s.close()
    print(f"\nWrote: {args.out}")

if __name__=="__main__":
    main()
