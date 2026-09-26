"""Compatibility wrapper for the physically verified Observe Right pose."""
from runtime.core.safety.existing_motions import (
    OBSERVE_RIGHT_ARM_TARGETS,
    OBSERVE_RIGHT_TARGETS,
)
from runtime.core.safety.production_motion import execute_named_pose


TARGETS = OBSERVE_RIGHT_TARGETS
ARM_ONLY_TARGETS = OBSERVE_RIGHT_ARM_TARGETS


def arm_observe_right():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_right():
    return execute_named_pose("observe_right_arm_only", ARM_ONLY_TARGETS)
