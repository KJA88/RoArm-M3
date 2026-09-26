"""Compatibility wrapper for the physically verified scan-right sequence."""
from runtime.core.safety.existing_motions import (
    READY_ARM_TARGETS,
    READY_TARGETS,
    SCAN_RIGHT_BASE_TARGET,
)
from runtime.core.safety.production_motion import execute_named_sequence


RIGHT_BASE_TARGET = SCAN_RIGHT_BASE_TARGET


def arm_scan_right():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_scan_right():
    return execute_named_sequence(
        "scan_right_arm_only",
        (
            ("ready_arm_only", READY_ARM_TARGETS),
            ("scan_right", RIGHT_BASE_TARGET),
        ),
    )
