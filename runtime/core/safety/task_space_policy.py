"""Fixed-purpose production policy for the first firmware-IK probe."""
import math


TASK_SPACE_BOUNDS = {
    "x": (150.0, 480.0),
    "y": (-400.0, 400.0),
    "z": (20.0, 500.0),
    "pitch": (-1.57, 1.57),
}
TASK_PROBE_CENTER = {
    "name": "task_probe_center",
    "x": 250.0,
    "y": 0.0,
    "z": 250.0,
    "pitch": 0.0,
}


def validate_task_space_target(target):
    if (
        not isinstance(target, dict)
        or set(target) != {"name", *TASK_SPACE_BOUNDS}
        or not isinstance(target.get("name"), str)
    ):
        return False
    return all(
        _finite(target[field])
        and minimum <= float(target[field]) <= maximum
        for field, (minimum, maximum) in TASK_SPACE_BOUNDS.items()
    )


def is_task_probe_center(target):
    return validate_task_space_target(target) and all(
        target[field] == expected
        for field, expected in TASK_PROBE_CENTER.items()
    )


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


__all__ = [
    "TASK_PROBE_CENTER",
    "TASK_SPACE_BOUNDS",
    "is_task_probe_center",
    "validate_task_space_target",
]
