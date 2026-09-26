"""Human-verified, named-only production gripper policy."""
import json
import math
from pathlib import Path


DEFAULT_GRIPPER_MAP_PATH = (
    Path(__file__).resolve().parents[1] / "calibration" / "gripper_map.json"
)
GRIPPER_PRESET_NAMES = {"open", "light", "firm", "pinch"}


def load_verified_gripper_presets(path=None):
    source = DEFAULT_GRIPPER_MAP_PATH if path is None else Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    gripper = data["gripper"]
    presets = gripper["presets"]
    minimum = gripper["safe_min"]
    maximum = gripper["safe_max"]
    if (
        gripper.get("verified_by") != "human"
        or gripper.get("units") != "radians"
        or set(presets) != GRIPPER_PRESET_NAMES
        or not _finite(minimum)
        or not _finite(maximum)
        or minimum > maximum
        or any(
            not _finite(value) or not minimum <= value <= maximum
            for value in presets.values()
        )
    ):
        raise ValueError("GRIPPER_MAP_NOT_VERIFIED")
    return {name: float(presets[name]) for name in sorted(presets)}


def resolve_gripper_preset(preset, path=None):
    if not isinstance(preset, str):
        raise ValueError("GRIPPER_PRESET_INVALID")
    presets = load_verified_gripper_presets(path)
    if preset not in presets:
        raise ValueError("GRIPPER_PRESET_NOT_AUTHORIZED")
    return presets[preset]


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


__all__ = [
    "DEFAULT_GRIPPER_MAP_PATH",
    "GRIPPER_PRESET_NAMES",
    "load_verified_gripper_presets",
    "resolve_gripper_preset",
]
