#!/usr/bin/env python3
import serial, json, time, math

PORT = "/dev/ttyUSB0"   # adjust if needed

def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))

def main():
    ser = serial.Serial(PORT, baudrate=115200, timeout=0.05)
    time.sleep(0.5)

    # 1) Make sure torque is ON
    send(ser, {"T":210, "cmd":1})
    time.sleep(0.2)

    # 2) Go to start point of circle using the blocking 104 (so we start from a known pose)
    start = {"T":104, "x":285, "y":0, "z":234, "t":0, "r":0, "g":1.07, "spd":0.6}
    send(ser, start)
    time.sleep(2.0)   # give it time to get there

    # 3) Circle parameters (same as your log)
    cx, cy, cz = 235.0, 0.0, 234.0   # center
    R = 50.0                          # radius
    steps = 180                       # more steps = smoother circle
    dt = 0.03                         # ~33 Hz

    # 4) Stream 1041 direct control points
    for i in range(steps):
        theta = 2 * math.pi * (i / steps)
        x = cx + R * math.cos(theta)
        y = cy + R * math.sin(theta)
        z = cz                        # keep Z constant for now

        cmd = {
            "T": 1041,
            "x": x,
            "y": y,
            "z": z,
            "t": 0,
            "r": 0,
            "g": 1.07,   # roughly your current gripper angle from feedback
        }
        send(ser, cmd)
        time.sleep(dt)

    # 5) Go back to candle
    home = {"T":104, "x":48.9, "y":0, "z":552.6, "t":-1.56, "r":-0.0015, "g":1.07, "spd":0.6}
    send(ser, home)
    time.sleep(2.0)

    ser.close()

if __name__ == "__main__":
    main()
