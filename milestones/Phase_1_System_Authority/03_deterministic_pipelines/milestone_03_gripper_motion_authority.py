"""Compatibility wrapper pending explicit gripper-policy review.

The human-verified Milestone 02 gripper calibration remains authoritative;
this wrapper reports it but does not silently grant motion authority from it.
"""
from runtime.core.safety.production_motion import inspect_gripper


def arm_gripper_motion():
    return {
        "armed": False,
        "reason": "GRIPPER_POLICY_REVIEW_REQUIRED",
        "sha256": None,
    }


def execute_gripper_position(position):
    return inspect_gripper(position)
