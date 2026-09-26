"""Compatibility wrapper for the physically verified Ready pose."""
from runtime.core.safety.existing_motions import (
    READY_ARM_TARGETS,
    READY_TARGETS,
)
from runtime.core.safety.production_motion import execute_named_pose


def arm_ready():
    return {
        "armed": False,
        "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION",
        "sha256": None,
    }


def execute_ready():
    return execute_named_pose("ready_arm_only", READY_ARM_TARGETS)
