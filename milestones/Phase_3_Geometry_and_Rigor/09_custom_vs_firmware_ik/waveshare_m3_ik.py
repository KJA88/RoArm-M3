"""Upstream Waveshare M3 inverse kinematics, transcribed without fitting.

Source: waveshareteam/roarm_ws commit fc2b0e40
File: src/roarm_main/roarm_moveit_cmd/include/roarm_moveit_cmd/solver.hpp
Symbol: roarm_m3::computeJointRadbyPos

The header returns one acos branch. It does not take a seed pose.
The reflected-acos triangle is computed here only so that branch can be
identified. The header does not return it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from waveshare_m3_fk import L2, L3, LE, T2, T3, TE, upstream_fk

# Literal in computeJointRadbyPos. The vision Python file uses math.pi instead.
HEADER_PITCH_OFFSET = 3.1416


@dataclass(frozen=True)
class IkSolution:
    base: float
    shoulder: float
    elbow: float
    wrist: float
    roll: float
    nan_ik: bool
    exposed_by_header: bool
    label: str


def header_ik(x: float, y: float, z: float, roll: float, pitch: float) -> IkSolution:
    return _solve(x, y, z, roll, pitch, reflect=False, exposed=True, label="header_acos")


def reflected_triangle(x: float, y: float, z: float, roll: float, pitch: float) -> IkSolution:
    """Same triangle with the opposite acos signs. Not returned by the header."""
    return _solve(x, y, z, roll, pitch, reflect=True, exposed=False, label="reflected_acos_not_returned")


def _solve(x, y, z, roll, pitch, reflect, exposed, label) -> IkSolution:
    try:
        delta_x, delta_y = _rotate_point(pitch - HEADER_PITCH_OFFSET)
        beta_x, beta_y = _move_point(x, y, delta_x)
        radius, theta = _cartesian_to_polar(beta_x, beta_y)
        shoulder, elbow, buffer = _linkage(radius, z + delta_y, reflect)
    except ValueError:
        return IkSolution(math.nan, math.nan, math.nan, math.nan, roll, True, exposed, label)
    values = (theta, shoulder, elbow, buffer)
    nan_ik = any(math.isnan(value) for value in values)
    return IkSolution(theta, shoulder, elbow, buffer + pitch, roll, nan_ik, exposed, label)


def _rotate_point(theta: float) -> tuple[float, float]:
    alpha = TE + theta
    return -LE * math.cos(alpha), -LE * math.sin(alpha)


def _move_point(x_a: float, y_a: float, shift: float) -> tuple[float, float]:
    distance = math.hypot(x_a, y_a)
    if distance - shift <= 1e-6:
        return 0.0, 0.0
    ratio = (distance - shift) / distance
    return x_a * ratio, y_a * ratio


def _cartesian_to_polar(x: float, y: float) -> tuple[float, float]:
    return math.hypot(x, y), math.atan2(y, x)


def _linkage(a_in: float, b_in: float, reflect: bool) -> tuple[float, float, float]:
    sign = -1.0 if reflect else 1.0
    if abs(b_in) < 1e-6:
        psi = sign * math.acos((L2 * L2 + a_in * a_in - L3 * L3) / (2 * L2 * a_in)) + T2
        alpha = math.pi / 2.0 - psi
        omega = sign * math.acos((a_in * a_in + L3 * L3 - L2 * L2) / (2 * a_in * L3))
        beta = psi + omega - T3
    else:
        l2c = a_in * a_in + b_in * b_in
        lc = math.sqrt(l2c)
        lambd = math.atan2(b_in, a_in)
        psi = sign * math.acos((L2 * L2 + l2c - L3 * L3) / (2 * L2 * lc)) + T2
        alpha = math.pi / 2.0 - lambd - psi
        omega = sign * math.acos((L3 * L3 + l2c - L2 * L2) / (2 * lc * L3))
        beta = psi + omega - T3
    return alpha, beta, math.pi / 2.0 - alpha - beta


def fk_of(solution: IkSolution) -> tuple[float, float, float, float]:
    return upstream_fk(solution.base, solution.shoulder, solution.elbow, solution.wrist)
