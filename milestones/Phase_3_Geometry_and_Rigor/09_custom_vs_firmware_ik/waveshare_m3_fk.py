"""Upstream Waveshare M3 forward kinematics, transcribed without fitting.

Source: waveshareteam/roarm_ws
Ref: ros2-humble-develop-251125
Commit: fc2b0e40fab785f637dbd81918b79a0892c8f1f3
File: src/roarm_main/roarm_moveit_cmd/include/roarm_moveit_cmd/solver.hpp
Symbol: roarm_m3::computePosbyJointRad

The Python copy in roarm_vision/roarm_vision/roarm_solver.py uses the same FK.
ARM_L1_LENGTH_MM is defined upstream and is not an input to this FK.
"""

from __future__ import annotations

import math

ARM_L1_LENGTH_MM = 126.06
ARM_L2_LENGTH_MM_A = 236.82
ARM_L2_LENGTH_MM_B = 30.00
ARM_L3_LENGTH_MM_A = 144.49
ARM_L3_LENGTH_MM_B = 0.0
ARM_L4_LENGTH_MM_A = 171.67
ARM_L4_LENGTH_MM_B = 13.69

L2 = math.hypot(ARM_L2_LENGTH_MM_A, ARM_L2_LENGTH_MM_B)
T2 = math.atan2(ARM_L2_LENGTH_MM_B, ARM_L2_LENGTH_MM_A)
L3 = math.hypot(ARM_L3_LENGTH_MM_A, ARM_L3_LENGTH_MM_B)
T3 = math.atan2(ARM_L3_LENGTH_MM_B, ARM_L3_LENGTH_MM_A)
LE = math.hypot(ARM_L4_LENGTH_MM_A, ARM_L4_LENGTH_MM_B)
TE = math.atan2(ARM_L4_LENGTH_MM_B, ARM_L4_LENGTH_MM_A)


def upstream_fk(base: float, shoulder: float, elbow: float, wrist: float) -> tuple[float, float, float, float]:
    """Return x, y, z millimeters and pitch radians. Roll and gripper do not enter."""
    a_out, b_out = _polar(L2, math.pi / 2 - (shoulder + T2))
    c_out, d_out = _polar(L3, math.pi / 2 - (elbow + shoulder + T3))
    e_out, f_out = _polar(LE, math.pi / 2 - (elbow + shoulder + wrist + TE))
    radius = a_out + c_out + e_out
    z = b_out + d_out + f_out
    x, y = _polar(radius, base)
    pitch = elbow + shoulder + wrist - math.pi / 2
    return x, y, z, pitch


def _polar(radius: float, theta: float) -> tuple[float, float]:
    return radius * math.cos(theta), radius * math.sin(theta)
