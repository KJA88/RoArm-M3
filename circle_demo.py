# Quick tuning knobs (make it look pro)
# 
# In the working script, tweak these:
#   steps = 180    # more steps → smoother
#   dt = 0.03      # smaller dt → faster (higher frequency)
#   R = 50.0       # circle radius
#
# Examples:
#   Smoother: steps = 360
#   Faster:   dt = 0.02 or 0.015
#   Bigger circle (if workspace allows): R = 70.0
#
# 3D helix (Z moving):
#   AMP = 20.0  # mm of vertical swing
#   for i in range(steps):
#       theta = 2 * math.pi * (i / steps)
#       x = cx + R * math.cos(theta)
#       y = cy + R * math.sin(theta)
#       z = cz + AMP * math.sin(theta)
#
# Why this is a big deal (hireable story):
#   - Streaming Cartesian controller using T=1041 (native IK)
#   - Real-time path generation using cos/sin
#   - Clean separation: path → command → firmware → motion
#   - Great README bullet for interviews


#!/usr/bin/env python3
"""
Circle / helix demo over UART using T=104 and T=1041.

What it does:
  1) Torque ON (T=210)
  2) Move to a known start pose with blocking T=104
  3) Stream a circular or helical trajectory using T=1041
     - By default: 3 full revolutions
  4) Go back to candle pose with T=104
  5) Request one T=105 feedback packet and print XYZ
"""

import serial
import json
import time
import math

PORT = "/dev/ttyUSB0"   # adjust if needed


def send(ser, cmd: dict):
    """Send one JSON command over UART."""
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))


def main():
    ser = serial.Serial(PORT, baudrate=115200, timeout=0.05)
    time.sleep(0.5)

    # -------------------------------
    # 1) Torque ON
    # -------------------------------
    send(ser, {"T": 210, "cmd": 1})
    time.sleep(0.2)

    # -------------------------------
    # 2) Go to start point of circle
    #    (blocking T=104 so we start from a known pose)
    # -------------------------------
    start = {
        "T": 104,
        "x": 285,
        "y": 0,
        "z": 234,
        "t": 0,
        "r": 0,
        "g": 1.07,
        "spd": 0.6,
    }
    send(ser, start)
    time.sleep(2.0)  # give it time to get there

    # -------------------------------
    # 3) Trajectory parameters
    # -------------------------------
    cx, cy, cz = 235.0, 0.0, 234.0   # center of circle
    R = 100.0                        # radius (mm) - doubled

    steps = 180          # points per revolution
    REVOLUTIONS = 3      # number of laps
    dt = 0.04            # seconds between points (~25 Hz) - slower

    AMP = 20.0           # helix vertical swing (mm).
                         # Set AMP = 0.0 for a flat circle.

    print(f"Streaming trajectory: {REVOLUTIONS} revolutions, "
          f"{steps} steps/rev, dt={dt}, R={R}, AMP={AMP}")

    # -------------------------------
    # 4) Stream T=1041 points
    # -------------------------------
    total_steps = steps * REVOLUTIONS

    for i in range(total_steps):
        # i/steps increases by 1 per revolution → cos/sin wrap every 2π
        theta = 2.0 * math.pi * (i / steps)

        x = cx + R * math.cos(theta)
        y = cy + R * math.sin(theta)
        z = cz + AMP * math.sin(theta)  # helix; use AMP=0 for flat circle

        cmd = {
            "T": 1041,
            "x": x,
            "y": y,
            "z": z,
            "t": 0,
            "r": 0,
            "g": 1.07,  # roughly your current gripper angle from feedback
        }
        send(ser, cmd)
        time.sleep(dt)

    # -------------------------------
    # 5) Go back to candle pose
    # -------------------------------
    home = {
        "T": 104,
        "x": 48.9,
        "y": 0,
        "z": 552.6,
        "t": -1.56,
        "r": -0.0015,
        "g": 1.07,
        "spd": 0.6,
    }
    send(ser, home)
    time.sleep(2.0)

    # -------------------------------
    # 6) Request one feedback packet (T=105)
    # -------------------------------
    print("Requesting feedback at end of demo...")
    send(ser, {"T": 105})
    time.sleep(0.1)

    # Read a couple of lines; board usually echoes T=105 then T=1051
    raw_lines = []
    for i in range(3):
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f"Raw feedback line {i}: {line}")
            raw_lines.append(line)

    # Try to parse the last JSON-looking line
    feedback = None
    for line in reversed(raw_lines):
        if line.startswith("{") and line.endswith("}"):
            try:
                feedback = json.loads(line)
                break
            except json.JSONDecodeError as e:
                print("Could not parse JSON line:", e)

    if feedback is not None and feedback.get("T") == 1051:
        x = feedback.get("x")
        y = feedback.get("y")
        z = feedback.get("z")
        print(f"Feedback XYZ: x={x:.1f}, y={y:.1f}, z={z:.1f}")
    else:
        print("No valid T=1051 feedback parsed.")

    ser.close()
    print("Done.")


if __name__ == "__main__":
    main()
