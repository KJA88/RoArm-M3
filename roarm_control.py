import serial, time, json, argparse, sys
import numpy as np

PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 0.05

# ---------------------------------------------------------
# Utility: open serial
# ---------------------------------------------------------
def open_ser():
    try:
        return serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    except Exception as e:
        print("ERROR opening serial:", e)
        sys.exit(1)

# ---------------------------------------------------------
# SEND RAW JSON EXACTLY AS ROBOT EXPECTS
# ---------------------------------------------------------
def send_json(ser, data):
    msg = json.dumps(data) + "\n"
    print("SEND:", msg.strip())
    ser.write(msg.encode("utf-8"))
    time.sleep(0.05)

# ---------------------------------------------------------
# JOINT COMMAND (correct keys!)
# ---------------------------------------------------------
def move_joints(ser, b, s, e, t, r, g, spd=0.5, acc=10):
    cmd = {
        "T":102,
        "b": b,
        "s": s,
        "e": e,
        "t": t,
        "r": r,
        "g": g,
        "spd": spd,
        "acc": acc
    }
    send_json(ser, cmd)

# ---------------------------------------------------------
# Torque control
# ---------------------------------------------------------
def torque_on(ser):
    send_json(ser, {"T":103, "cmd":1})

def torque_off(ser):
    send_json(ser, {"T":103, "cmd":0})

# ---------------------------------------------------------
# MAIN CLI
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["joints", "torque_on", "torque_off"])
    parser.add_argument("vals", nargs="*")
    args = parser.parse_args()

    ser = open_ser()

    if args.mode == "torque_on":
        torque_on(ser)
        return
    if args.mode == "torque_off":
        torque_off(ser)
        return

    if args.mode == "joints":
        if len(args.vals) < 6:
            print("Need 6 joint values: b s e t r g")
            return

        b, s, e, t, r, g = map(float, args.vals)
        move_joints(ser, b, s, e, t, r, g)

if __name__ == "__main__":
    main()
