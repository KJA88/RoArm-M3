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


#!/usr/bin/env python3


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

Quick tuning knobs:
  steps        - points per revolution (more -> smoother)
  dt           - seconds between points (smaller -> faster / higher frequency)
  R            - circle radius in mm
  AMP          - vertical swing in mm (0 -> flat circle, >0 -> helix)
  REVOLUTIONS  - how many laps

Safety:
  - Gripper angle is clamped to GRIPPER_MIN to avoid stall.
  - GRIPPER_CMD sets how closed the gripper is during the demo.
"""

import serial
import json
import time
import math

# -------------------------------
# Config
# -------------------------------

PORT = "/dev/ttyUSB0"   # adjust if needed
BAUD = 115200

# Gripper safety + command
GRIPPER_MIN = 1.2   # hard safety minimum (stall danger below this)
GRIPPER_CMD = 3.0   # desired operating angle (more closed, < 3.2 rad)

# Start pose for the circle (blocking T=104)
START_POSE = {
    "x": 285.0,
    "y": 0.0,
    "z": 234.0,
    "t": 0.0,
    "r": 0.0,
    "g": GRIPPER_CMD,
    "spd": 0.6,
}

# Candle pose to return to after the demo (T=104)
CANDLE_POSE = {
    "x": 48.9,
    "y": 0.0,
    "z": 552.6,
    "t": -1.56,
    "r": -0.0015,
    "g": GRIPPER_CMD,
    "spd": 0.6,
}

# Circle / helix parameters
CX, CY, CZ = 235.0, 0.0, 234.0   # center of circle in mm
R = 100.0                        # radius (mm)
AMP = 20.0                       # helix vertical swing (mm). 0.0 -> flat circle
STEPS = 180                      # points per revolution
REVOLUTIONS = 3                  # number of laps
DT = 0.04                        # seconds between points (~25 Hz)


# -------------------------------
# UART helper
# -------------------------------

def send(ser: serial.Serial, cmd: dict) -> None:
    """Send one JSON command over UART with newline."""
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))


def safe_gripper_angle(g: float) -> float:
    """
    Ensure gripper angle is:
      - at least GRIPPER_MIN (stall safety)
      - whatever command value you choose (GRIPPER_CMD) or above
    """
    if g < GRIPPER_MIN:
        return GRIPPER_MIN
    return g


# -------------------------------
# Main demo
# -------------------------------

def main() -> None:
    ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.05)
    time.sleep(0.5)

    # 1) Torque ON
    send(ser, {"T": 210, "cmd": 1})
    time.sleep(0.2)

    # 2) Go to start point of circle (blocking T=104)
    start = {
        "T": 104,
        "x": START_POSE["x"],
        "y": START_POSE["y"],
        "z": START_POSE["z"],
        "t": START_POSE["t"],
        "r": START_POSE["r"],
        "g": safe_gripper_angle(START_POSE["g"]),
        "spd": START_POSE["spd"],
    }
    send(ser, start)
    time.sleep(2.0)  # give it time to get there

    # 3) Announce trajectory parameters
    print(
        f"Streaming trajectory: {REVOLUTIONS} revolutions, "
        f"{STEPS} steps/rev, dt={DT}, R={R}, AMP={AMP}, "
        f"gripper={safe_gripper_angle(GRIPPER_CMD):.2f} rad"
    )

    # 4) Stream T=1041 points
    total_steps = STEPS * REVOLUTIONS

    for i in range(total_steps):
        theta = 2.0 * math.pi * (i / STEPS)

        x = CX + R * math.cos(theta)
        y = CY + R * math.sin(theta)
        z = CZ + AMP * math.sin(theta)  # AMP=0 -> flat circle, >0 -> helix

        cmd = {
            "T": 1041,
            "x": x,
            "y": y,
            "z": z,
            "t": 0.0,
            "r": 0.0,
            "g": safe_gripper_angle(GRIPPER_CMD),
        }
        send(ser, cmd)
        time.sleep(DT)

    # 5) Go back to candle pose
    home = {
        "T": 104,
        "x": CANDLE_POSE["x"],
        "y": CANDLE_POSE["y"],
        "z": CANDLE_POSE["z"],
        "t": CANDLE_POSE["t"],
        "r": CANDLE_POSE["r"],
        "g": safe_gripper_angle(CANDLE_POSE["g"]),
        "spd": CANDLE_POSE["spd"],
    }
    send(ser, home)
    time.sleep(2.0)

    # 6) Request one feedback packet (T=105)
    print("Requesting feedback at end of demo...")
    send(ser, {"T": 105})
    time.sleep(0.1)

    raw_lines = []
    for i in range(3):
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f"Raw feedback line {i}: {line}")
            raw_lines.append(line)

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
