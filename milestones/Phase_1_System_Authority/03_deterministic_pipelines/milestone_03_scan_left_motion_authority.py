"""Compatibility wrapper for the physically verified scan-left sequence."""
from runtime.core.safety.existing_motions import (
    READY_ARM_TARGETS,
    READY_TARGETS,
    SCAN_LEFT_BASE_TARGET,
)
from runtime.core.safety.production_motion import execute_named_sequence


LEFT_BASE_TARGET = SCAN_LEFT_BASE_TARGET


def arm_scan_left():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_scan_left():
    return execute_named_sequence(
        "scan_left_arm_only",
        (
            ("ready_arm_only", READY_ARM_TARGETS),
            ("scan_left", LEFT_BASE_TARGET),
        ),
    )
