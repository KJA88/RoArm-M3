#!/usr/bin/env python3
"""
XY Calibration Point Runner

- Moves robot through predefined XY points
- Z fixed
- Waits for ENTER between moves
- Designed to be used alongside collect_samples.py

Usage:
  Terminal 1: python3 collect_samples.py
  Terminal 2: ./run_xy_calibration_points.py
"""

import time
import json
import serial

# ===============================
# ROBOT SERIAL CONFIG
# ===============================
PORT = "/dev/ttyUSB0"
BAUD = 115200
MOVE_DELAY = 0.5  # seconds after move command

# ===============================
# CALIBRATION POINTS
# ===============================
Z_FIXED = 100.0

POINTS = [
    (100, -200),
    (250, -200),
    (400, -200),

    (100,    0),
    (250,    0),
    (400,    0),

    (100,  200),
    (250,  200),
    (400,  200),
]

# ===============================
# SERIAL HELPER
# ===============================
def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))

# ===============================
# MAIN
# ===============================
def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.5)

    print("\n=== XY CALIBRATION RUNNER ===")
    print(f"Z fixed at {Z_FIXED}")
    print("Press ENTER to move to each point.")
    print("Use Ctrl+C to abort.\n")

    try:
        for i, (x, y) in enumerate(POINTS, start=1):
            input(f"[{i}/{len(POINTS)}] Press ENTER to move to X={x}, Y={y} ...")

            send(ser, {
                "T": 1041,
                "x": float(x),
                "y": float(y),
                "z": Z_FIXED,
                "t": 0.0,
                "r": 0.0,
                "g": 3.0
            })

            time.sleep(MOVE_DELAY)
            print(f"Moved to ({x}, {y}, {Z_FIXED})")

        print("\nAll calibration points completed.")

    except KeyboardInterrupt:
        print("\nCalibration runner aborted by user.")

    finally:
        ser.close()

if __name__ == "__main__":
    main()
