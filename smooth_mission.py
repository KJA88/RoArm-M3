#!/usr/bin/env python3
import time
import sys
import os
import subprocess
from math import sqrt

# --- Configuration ---
ROARM_CONTROL_SCRIPT = "./roarm_control.py"
SAFE_ROLL = 0.0
STEP_SIZE_MM = 3.0      # Distance per micro-step (industry standard)
STEP_DELAY = 0.02       # 20 ms between each micro-step (safe & smooth)

# -----------------------------
# Distance-Based Interpolation
# -----------------------------
def interpolate_points(p1, p2, step_size=STEP_SIZE_MM):
    """
    Returns a list of micro-steps between p1 → p2 spaced by `step_size` mm.
    This ensures consistent smoothness regardless of total distance.
    """
    x1, y1, z1 = p1["x"], p1["y"], p1["z"]
    x2, y2, z2 = p2["x"], p2["y"], p2["z"]

    # Distance between points
    dist = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

    # Number of micro-steps based on constant distance increments
    steps = max(1, int(dist / step_size))

    points = []
    for i in range(1, steps + 1):
        t = i / steps
        points.append({
            "x": x1 + t * (x2 - x1),
            "y": y1 + t * (y2 - y1),
            "z": z1 + t * (z2 - z1),
            "r": p2["r"],      # maintain target roll
            "g": p1["g"],      # maintain current gripper during motion
            "desc": f"Micro-step {i}/{steps}"
        })
    return points


# -----------------------------
# Execute a Single T=104 Move
# -----------------------------
def execute_move(point):
    """
    Calls roarm_control.py move command (which uses T=104).
    This ensures blocking, safe IK-controlled movement for each micro-step.
    """
    cmd = [
        sys.executable,
        ROARM_CONTROL_SCRIPT,
        "move",
        str(point["x"]),
        str(point["y"]),
        str(point["z"]),
        str(point["r"]),
        str(point["g"])
    ]

    subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        env=os.environ,
        timeout=10
    )


# -----------------------------
# Execute Interpolated Motion
# -----------------------------
def interpolate_and_execute(p1, p2):
    """
    Uses distance-based interpolation to move from p1 → p2 smoothly.
    """
    # If only gripping (XYZ fixed), skip interpolation
    if p1["x"] == p2["x"] and p1["y"] == p2["y"] and p1["z"] == p2["z"] and p1["g"] != p2["g"]:
        print(f"\n--- Gripper Action: {p2['desc']} ---")
        execute_move(p2)
        return

    # Generate smooth micro-steps
    micro_steps = interpolate_points(p1, p2, step_size=STEP_SIZE_MM)

    print(f"\n--- Smooth Motion: {p1['desc']} → {p2['desc']} ({len(micro_steps)} micro-steps) ---")

    # Execute micro-steps
    for step in micro_steps:
        execute_move(step)
        time.sleep(STEP_DELAY)

    # Execute final endpoint exactly (for correct g)
    execute_move(p2)


# -----------------------------
# Mission Runner
# -----------------------------
def run_mission(mission):
    print("\n--- Starting Hybrid Smooth Mission ---")

    # Enable torque (safety)
    subprocess.run([sys.executable, "./torque_on.py"], check=True, env=os.environ)

    previous = mission[0]
    execute_move(previous)  # Move to initial point
    time.sleep(1)

    # Execute each segment with interpolation
    for i in range(1, len(mission)):
        current = mission[i]
        interpolate_and_execute(previous, current)
        previous = current

    print("\n--- Mission Complete ---")


# -----------------------------
# Mission Definition
# -----------------------------
MISSION_SEQUENCE = [
    {"x":200, "y":0,   "z":200, "r":SAFE_ROLL, "g":0.5, "desc":"Home Start"},
    {"x":250, "y":0,   "z":150, "r":SAFE_ROLL, "g":0.5, "desc":"Approach A"},
    {"x":250, "y":0,   "z":100, "r":SAFE_ROLL, "g":0.5, "desc":"Pick A"},
    {"x":250, "y":0,   "z":100, "r":SAFE_ROLL, "g":3.0, "desc":"Grip"},
    {"x":250, "y":0,   "z":180, "r":SAFE_ROLL, "g":3.0, "desc":"Lift"},
    {"x":100, "y":150, "z":180, "r":SAFE_ROLL, "g":3.0, "desc":"Approach B"},
    {"x":100, "y":150, "z":100, "r":SAFE_ROLL, "g":3.0, "desc":"Drop B"},
    {"x":100, "y":150, "z":100, "r":SAFE_ROLL, "g":0.5, "desc":"Release"},
    {"x":100, "y":150, "z":180, "r":SAFE_ROLL, "g":0.5, "desc":"Retreat"},
    {"x":200, "y":0,   "z":200, "r":SAFE_ROLL, "g":0.5, "desc":"Return Home"}
]

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    run_mission(MISSION_SEQUENCE)
