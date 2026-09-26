"""FK-only comparison of the upstream Waveshare M3 model to recorded T105 states.

No hardware. No production imports. Lengths and joint zeros are the upstream
values. Historical planar offsets are not applied.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from waveshare_m3_fk import ARM_L1_LENGTH_MM, upstream_fk

# Historical 20-row fit. Documented so it is not confused with
# runtime/core/calibration/planar_calib.json, which is a different sketch.
HISTORICAL_FITTED_PLANAR = {
    "L1": 238.839,
    "L2": 316.731,
    "X0": -0.186,
    "Z0": -0.371,
    "shoulder_offset": 0.126072,
    "elbow_offset": -0.085031,
    "source": "docs/02_NOTES_INTERNAL/roarm_kinematics_control_log.json latest_known_good_fit",
    "runtime_sketch": "runtime/core/calibration/planar_calib.json",
}


@dataclass(frozen=True)
class RecordedState:
    name: str
    b: float
    s: float
    e: float
    t: float
    x: float
    y: float
    z: float
    tit: float


# READY, center, Z200, Z300, and X300 match m05_results.json.
# CANDLE is the recorded state supplied for this comparison.
RECORDED = (
    RecordedState("READY", -0.001533981, -0.829883606, 2.405281875, 0.016873789, 161.3352596, -0.247485383, 163.9417706, 0.021475731),
    RecordedState("CANDLE", -0.004601942, 0.001533981, 0.006135923, 0.001533981, 46.7404, -0.2151, 552.7962, -1.56159),
    RecordedState("CENTER", -0.001533981, -0.391165101, 1.768679848, 0.228563137, 250.3220502, -0.383989517, 238.3865744, 0.035281558),
    RecordedState("Z200", -0.001533981, -0.394233062, 2.089281833, -0.099708751, 251.3942329, -0.385634226, 194.3709341, 0.024543693),
    RecordedState("Z300", -0.001533981, -0.305262177, 1.339165228, 0.573708815, 252.6484006, -0.387558097, 288.7903948, 0.036815539),
    RecordedState("X300", -0.001533981, -0.181009733, 1.61681575, 0.188679637, 300.7399995, -0.461329743, 234.9144945, 0.053689328),
)


def _error(predicted, state: RecordedState) -> dict:
    dx = predicted[0] - state.x
    dy = predicted[1] - state.y
    dz = predicted[2] - state.z
    return {
        "x": predicted[0],
        "y": predicted[1],
        "z": predicted[2],
        "pitch": predicted[3],
        "dx": dx,
        "dy": dy,
        "dz": dz,
        "norm": math.sqrt(dx * dx + dy * dy + dz * dz),
        "pitch_error": predicted[3] - state.tit,
    }


def raw_rows():
    return [{"name": state.name, **_error(upstream_fk(state.b, state.s, state.e, state.t), state)} for state in RECORDED]


def _max_norm(transform) -> float:
    norms = []
    for state in RECORDED:
        b, s, e, t = transform(state)
        norms.append(_error(upstream_fk(b, s, e, t), state)["norm"])
    return max(norms)


def sign_trials() -> dict[str, float]:
    """Explicit sign flips. Not a search for an offset."""
    return {
        "as_published": _max_norm(lambda s: (s.b, s.s, s.e, s.t)),
        "flip_base": _max_norm(lambda s: (-s.b, s.s, s.e, s.t)),
        "flip_shoulder": _max_norm(lambda s: (s.b, -s.s, s.e, s.t)),
        "flip_elbow": _max_norm(lambda s: (s.b, s.s, -s.e, s.t)),
        "flip_wrist": _max_norm(lambda s: (s.b, s.s, s.e, -s.t)),
    }


def pitch_conventions() -> dict[str, float]:
    """Max absolute pitch error under explicit formulas. Position is unchanged."""
    formulas = {
        "s_plus_e_plus_t_minus_pi_over_2": lambda s, e, t: s + e + t - math.pi / 2,
        "s_plus_e_plus_t": lambda s, e, t: s + e + t,
        "negated_upstream_pitch": lambda s, e, t: -(s + e + t - math.pi / 2),
    }
    result = {}
    for name, formula in formulas.items():
        result[name] = max(abs(formula(state.s, state.e, state.t) - state.tit) for state in RECORDED)
    return result


def base_height_trials() -> dict[str, float]:
    """Add a published vertical constant to Z. These are not fitted."""
    shifts = {
        "as_published": 0.0,
        "add_unused_solver_L1_126_06": ARM_L1_LENGTH_MM,
        "add_urdf_base_stack_123_559": 71.6 + 51.959,
    }
    result = {}
    for name, shift in shifts.items():
        norms = []
        for state in RECORDED:
            x, y, z, pitch = upstream_fk(state.b, state.s, state.e, state.t)
            norms.append(_error((x, y, z + shift, pitch), state)["norm"])
        result[name] = max(norms)
    return result


def ready_low_wrist_shift_mm() -> float:
    """Distance between FK at the recorded READY wrist and at 0.0015 rad."""
    ready = RECORDED[0]
    published = upstream_fk(ready.b, ready.s, ready.e, ready.t)
    low = upstream_fk(ready.b, ready.s, ready.e, 0.0015)
    return math.dist(published[:3], low[:3])


def format_table() -> str:
    lines = [
        "pose      pred_x      pred_y      pred_z     pitch    dx_mm    dy_mm    dz_mm   norm_mm  pitch_err",
    ]
    for row in raw_rows():
        lines.append(
            f"{row['name']:8} {row['x']:11.4f} {row['y']:11.4f} {row['z']:11.4f} {row['pitch']:9.5f} "
            f"{row['dx']:11.3e} {row['dy']:11.3e} {row['dz']:11.3e} {row['norm']:11.3e} {row['pitch_error']:11.3e}"
        )
    lines.append("")
    lines.append("max XYZ norm by explicit convention trial, mm")
    for name, value in sign_trials().items():
        lines.append(f"  sign {name:16} {value:.6f}")
    for name, value in base_height_trials().items():
        lines.append(f"  height {name:32} {value:.6f}")
    lines.append("max |pitch error| by explicit formula, rad")
    for name, value in pitch_conventions().items():
        lines.append(f"  {name:40} {value:.6e}")
    lines.append(f"READY wrist 0.0015 versus recorded wrist, FK shift mm: {ready_low_wrist_shift_mm():.4f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_table())
