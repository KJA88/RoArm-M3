"""Compatibility wrappers for legacy named motion tools."""
from runtime.core.safety.existing_motions import CANDLE_ARM_TARGETS
from runtime.core.safety.production_motion import (
    deny_unsupported,
    execute_named_pose,
)


CANDLE_TARGETS = CANDLE_ARM_TARGETS


def _local_permit_notice(action):
    return {
        "armed": False,
        "action": action,
        "reason": "LOCAL_PERMIT_ISSUED_DURING_EXECUTION",
        "sha256": None,
    }


def arm_lissajous():
    return _local_permit_notice("lissajous")


def arm_candle():
    return _local_permit_notice("candle")


def execute_lissajous():
    return deny_unsupported(
        "lissajous",
        reason="TRAJECTORY_POLICY_UNVERIFIED",
    )


def execute_candle():
    return execute_named_pose("candle", CANDLE_TARGETS)
