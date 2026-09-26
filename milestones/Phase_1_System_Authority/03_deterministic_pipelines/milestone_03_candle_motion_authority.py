"""Compatibility wrapper for the physically verified Candle arm pose."""
from runtime.core.safety.existing_motions import CANDLE_ARM_TARGETS
from runtime.core.safety.production_motion import execute_named_pose


def execute_candle():
    """Move only the four authorized arm joints; preserve roll and gripper."""
    return execute_named_pose("candle_arm_only", CANDLE_ARM_TARGETS)


__all__ = ["CANDLE_ARM_TARGETS", "execute_candle"]
