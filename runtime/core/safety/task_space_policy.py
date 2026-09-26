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
TASK_PROBE_Z200 = {
    "name": "task_probe_z200",
    "x": 250.0,
    "y": 0.0,
    "z": 200.0,
    "pitch": 0.0,
}
TASK_PROBE_Z300 = {
    "name": "task_probe_z300",
    "x": 250.0,
    "y": 0.0,
    "z": 300.0,
    "pitch": 0.0,
}
TASK_PROBE_X300 = {
    "name": "task_probe_x300",
    "x": 300.0,
    "y": 0.0,
    "z": 250.0,
    "pitch": 0.0,
}
NAMED_TASK_PROBES = {
    probe["name"]: probe
    for probe in (
        TASK_PROBE_Z200,
        TASK_PROBE_CENTER,
        TASK_PROBE_Z300,
        TASK_PROBE_X300,
    )
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


def is_named_task_probe(target):
    if not validate_task_space_target(target):
        return False
    expected = NAMED_TASK_PROBES.get(target["name"])
    return expected is not None and target == expected


def is_task_probe_center(target):
    return target == TASK_PROBE_CENTER


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


__all__ = [
    "NAMED_TASK_PROBES",
    "TASK_PROBE_CENTER",
    "TASK_PROBE_X300",
    "TASK_PROBE_Z200",
    "TASK_PROBE_Z300",
    "TASK_SPACE_BOUNDS",
    "is_named_task_probe",
    "is_task_probe_center",
    "validate_task_space_target",
]
