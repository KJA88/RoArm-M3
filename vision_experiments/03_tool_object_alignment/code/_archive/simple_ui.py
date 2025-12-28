#!/usr/bin/env python3
"""
Simple IK UI for RoArm-M3

- Direct XYZ input
- Uses IK → joint motion (NOT Cartesian pose_ctrl)
- Supports negative Z
- Torque-safe
- Intended as a sanity / calibration tool
"""

import time
from roarm_sdk.roarm import roarm

# ===============================
# CONFIG
# ===============================
PORT = "/dev/ttyUSB0"
BAUD = 115200

SPEED = 100
ACC   = 0

# ===============================
# INIT ARM
# ===============================
arm = roarm(
    roarm_type="roarm_m3",
    port=PORT,
    baudrate=BAUD
)

print("Torque ON")
arm.torque_set(1)

print("Move to init")
arm.move_init()
time.sleep(1.0)

print("\nSimple IK UI")
print("Enter: X Y Z R G")
print("(X,Y,Z in mm | R,G in radians)")
print("Example: 300 0 -100 0.0 3.0")
print("Type 'q' to quit\n")

# ===============================
# MAIN LOOP
# ===============================
while True:
    try:
        user = input("> ").strip()
        if user.lower() == "q":
            break

        parts = user.split()
        if len(parts) != 5:
            print("Invalid input. Expected 5 values.")
            continue

        x, y, z, r, g = map(float, parts)

        print(f"Commanding IK move → x={x:.1f}, y={y:.1f}, z={z:.1f}")

        # ---- IK MOVE (this is the key) ----
        arm.goto_xyz(
            x=x,
            y=y,
            z=z,
            r=r,
            g=g,
            speed=SPEED,
            acc=ACC
        )

        time.sleep(0.5)

        pose = arm.pose_get()
        if pose:
            print("Feedback:")
            print(pose)

    except KeyboardInterrupt:
        print("\nCtrl+C — exiting safely")
        break
    except Exception as e:
        print("Error:", e)

print("\nExited. Torque remains ON.")
