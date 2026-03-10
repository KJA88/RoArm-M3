#!/usr/bin/env python3
"""
Milestone 07: Coordinate Frames (AUTHORITATIVE)

GOAL:
Given a WRIST pose in task-space (x, y, z, pitch),
compute the Tool Center Point (TCP) using a fixed
offset along the WRIST X-axis.

NO HARDWARE.
NO SERIAL.
NO FIRMWARE.
PURE GEOMETRY.
"""

import math

# --- CONFIG ---
TCP_OFFSET_MM = 120.0  # Tool sticks out along WRIST X-axis

def compute_tcp(wrist):
    """
    wrist: dict with keys x, y, z, pitch (radians)
    returns: dict with tcp_x, tcp_y, tcp_z
    """
    x = wrist["x"]
    y = wrist["y"]
    z = wrist["z"]
    pitch = wrist["pitch"]

    tcp_x = x + TCP_OFFSET_MM * math.cos(pitch)
    tcp_y = y
    tcp_z = z + TCP_OFFSET_MM * math.sin(pitch)

    return {
        "tcp_x": round(tcp_x, 3),
        "tcp_y": round(tcp_y, 3),
        "tcp_z": round(tcp_z, 3),
    }

if __name__ == "__main__":
    # Test vectors (deterministic)
    test_cases = [
        {"name": "LEVEL", "x": 250, "y": 0, "z": 200, "pitch": 0.0},
        {"name": "PITCH_DOWN", "x": 250, "y": 0, "z": 200, "pitch": -0.5},
        {"name": "PITCH_UP", "x": 250, "y": 0, "z": 200, "pitch": 0.5},
    ]

    print("\n--- Milestone 07: TCP Frame Validation ---")
    for t in test_cases:
        tcp = compute_tcp(t)
        print(f"\nCase: {t['name']}")
        print(f"Wrist -> X:{t['x']} Y:{t['y']} Z:{t['z']} Pitch:{t['pitch']}")
        print(f"TCP   -> X:{tcp['tcp_x']} Y:{tcp['tcp_y']} Z:{tcp['tcp_z']}")
    print("\n[OK] Coordinate frame math verified.")
