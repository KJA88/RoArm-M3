"""Compatibility wrapper for named, human-verified gripper presets."""
from runtime.core.safety.production_motion import execute_gripper_position as _execute


def arm_gripper_motion():
    return {
        "armed": True,
        "authority": "MILESTONE_02_NAMED_PRESETS_ONLY",
        "sha256": None,
    }


def execute_gripper_position(position):
    return _execute(position)
