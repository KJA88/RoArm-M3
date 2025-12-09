#!/usr/bin/env python3
import time
import json
import serial
import numpy as np
from math import sqrt

from ik import inverse_kinematics

# ------------------------------
# CONFIGURATION
# ------------------------------

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
MISSION_NAME = "pick_n_place"

SAFE_ROLL = 0.0
STEP_SIZE_MM = 10.0     # <<< 10 mm micro-step size
SAFE_Z = 100

# ------------------------------
# WAYPOINTS
# ------------------------------
MISSION_SEQUENCE = [
    {"x": 200, "y": 0,   "z": 200, "r": SAFE_ROLL, "g": 0.5},   # Home
    {"x": 250, "y": 0,   "z": 150, "r": SAFE_ROLL, "g": 0.5},   # Approach A
    {"x": 250, "y": 0,   "z": 100, "r": SAFE_ROLL, "g": 0.5},   # Pick A
    {"x": 250, "y": 0,   "z": 100, "r": SAFE_ROLL, "g": 3.0},   # Grip
    {"x": 250, "y": 0,   "z": 180, "r": SAFE_ROLL, "g": 3.0},   # Lift
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 3.0},   # Approach B
    {"x": 100, "y": 150, "z": 100, "r": SAFE_ROLL, "g": 3.0},   # Drop B
    {"x": 100, "y": 150, "z": 100, "r": SAFE_ROLL, "g": 0.5},   # Release
    {"x": 100, "y": 150, "z": 180, "r": SAFE_ROLL, "g": 0.5},   # Retreat
    {"x": 200, "y": 0,   "z": 200, "r": SAFE_ROLL, "g": 0.5},   # Return home
]

# ------------------------------
# SERIAL WRITER
# ------------------------------

def send_json(s, d):
    """Send ONE JSON command through an already opened serial port."""
    pkt = json.dumps(d) + "\n"
    s.write(pkt.encode("utf-8"))
    s.flush()
    time.sleep(0.01)   # prevent ESP32 overload


# ------------------------------
# INTERPOLATION (CARTESIAN)
# ------------------------------

def interpolate_points(p1, p2, step=STEP_SIZE_MM):
    x1, y1, z1 = p1["x"], p1["y"], p1["z"]
    x2, y2, z2 = p2["x"], p2["y"], p2["z"]

    dist = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    n = max(1, int(dist / step))

    pts = []
    for i in range(1, n+1):
        t = i / n
        pts.append({
            "x": x1 + t*(x2-x1),
            "y": y1 + t*(y2-y1),
            "z": z1 + t*(z2-z1),
            "r": p2["r"],
            "g": p1["g"]
        })

    return pts


# ------------------------------
# JOINT GENERATOR (IK + linear interpolation)
# ------------------------------

def generate_joint_steps():
    """Return list of all joint microsteps for the full mission."""
    print("Solving IK for all major waypoints...")

    # First solve IK for each major point
    joint_targets = []
    for p in MISSION_SEQUENCE:
        xyz = np.array([p["x"], p["y"], p["z"]])
        joints = inverse_kinematics(xyz, p["r"])

        if joints is None:
            raise RuntimeError(f"IK FAILED at point {p}")

        full = np.array([joints[0], joints[1], joints[2], joints[3], joints[4], p["g"]])
        joint_targets.append(full)

    # Now interpolate IN JOINT SPACE
    print("Interpolating joint-space microsteps...")
    microsteps = []

    for i in range(len(joint_targets)-1):
        j1 = joint_targets[i]
        j2 = joint_targets[i+1]

        # joint distance
        d = np.linalg.norm(j2 - j1)
        n = max(1, int(d / 0.05))     # each microstep = about 0.05 rad total motion

        for k in range(1, n+1):
            t = k / n
            microsteps.append(j1 + t*(j2 - j1))

    return microsteps


# ------------------------------
# MAIN
# ------------------------------

def main():
    print("\n--- Building mission using DIRECT SERIAL ---")

    s = serial.Serial(PORT, 115200, timeout=1)
    time.sleep(1)

    # Enable torque
    send_json(s, {"T":210, "cmd":1})

    # Create mission file
    send_json(s, {"T":220, "name":MISSION_NAME})

    # Generate all microsteps
    all_joint_steps = generate_joint_steps()
    print(f"Total microsteps: {len(all_joint_steps)}")

    # Write each T=102 step into mission
    for j in all_joint_steps:
        cmd = {
            "T":102,
            "base":float(j[0]),
            "shoulder":float(j[1]),
            "elbow":float(j[2]),
            "wrist":float(j[3]),
            "roll":float(j[4]),
            "hand":float(j[5]),
            "spd":0,
            "acc":0
        }

        send_json(s, {"T":222, "name":MISSION_NAME, "step":json.dumps(cmd)})

    print("Mission written!")

    # Play mission
    send_json(s, {"T":242, "name":MISSION_NAME, "times":1})
    print("Mission started.")

    s.close()


if __name__ == "__main__":
    main()
