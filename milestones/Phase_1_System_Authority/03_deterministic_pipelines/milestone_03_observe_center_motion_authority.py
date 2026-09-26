"""Compatibility wrapper for the physically verified Observe Center pose."""
from runtime.core.safety.existing_motions import (
    OBSERVE_CENTER_ARM_TARGETS,
    OBSERVE_CENTER_TARGETS,
)
from runtime.core.safety.production_motion import execute_named_pose


TARGETS = OBSERVE_CENTER_TARGETS
ARM_ONLY_TARGETS = OBSERVE_CENTER_ARM_TARGETS


def arm_observe_center():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_center():
    return execute_named_pose("observe_center_arm_only", ARM_ONLY_TARGETS)
