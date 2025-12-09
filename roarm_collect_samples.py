#!/usr/bin/env python3
import csv, time, json, argparse
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--out", default="samples.csv")
    ap.add_argument("--spd", type=float, default=0.35)
    args=ap.parse_args()

    # Safe-ish grid (edit if you want)
    shoulders = [-0.6, -0.3, 0.0, 0.3, 0.6, 0.9]
    elbows    = [0.3, 0.6, 1.0, 1.4, 1.8, 2.2]

    s=open_serial(args.port)
    torque_lock(s, True)

    with open(args.out, "w", newline="") as f:
        w=csv.writer(f)
        w.writerow([
            "t_unix","base_cmd","shoulder_cmd","elbow_cmd",
            "x","y","z","tit","b_fb","s_fb","e_fb","t_fb","r_fb","g_fb"
        ])

        # start from candle-ish
        send_joints(s, 0.0, 0.0, 0.0, spd=args.spd)
        time.sleep(0.9)
        fb=get_feedback(s)
        if fb:
            w.writerow([time.time(),0.0,0.0,0.0, fb["x"],fb["y"],fb["z"],fb["tit"], fb["b"],fb["s"],fb["e"],fb["t"],fb["r"],fb["g"]])
            f.flush()

        for sh in shoulders:
            for el in elbows:
                print(f"cmd sh={sh:.3f} el={el:.3f}")
                send_joints(s, 0.0, sh, el, spd=args.spd)
                time.sleep(0.9)
                fb=get_feedback(s)
                if not fb:
                    print("  (no feedback)")
                    continue
                w.writerow([time.time(),0.0,sh,el, fb["x"],fb["y"],fb["z"],fb["tit"], fb["b"],fb["s"],fb["e"],fb["t"],fb["r"],fb["g"]])
                f.flush()
                print(f"  fb x={fb['x']:.3f} y={fb['y']:.3f} z={fb['z']:.3f}   s={fb['s']:.6f} e={fb['e']:.6f}")

    s.close()
    print(f"\nWrote: {args.out}")

if __name__=="__main__":
    main()
