"""Compatibility wrapper for the physically verified Observe Left pose."""
from runtime.core.safety.existing_motions import (
    OBSERVE_LEFT_ARM_TARGETS,
    OBSERVE_LEFT_TARGETS,
)
from runtime.core.safety.production_motion import execute_named_pose


TARGETS = OBSERVE_LEFT_TARGETS
ARM_ONLY_TARGETS = OBSERVE_LEFT_ARM_TARGETS


def arm_observe_left():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_left():
    return execute_named_pose("observe_left_arm_only", ARM_ONLY_TARGETS)
