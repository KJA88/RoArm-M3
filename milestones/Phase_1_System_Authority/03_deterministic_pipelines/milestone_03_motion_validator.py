#!/usr/bin/env python3

"""
Milestone 03 - Read-Only Motion Proposal Validator

Purpose:
    Evaluate hypothetical RoArm joint targets against the human-verified
    Milestone 02 mechanical limits.

IMPORTANT:
    This module NEVER communicates with the robot.
    It does NOT import serial.
    It does NOT enable torque.
    It does NOT send commands.
    It does NOT move hardware.

The validator currently has authority only for joints whose mechanical
limits were human-verified in Milestone 02:
    shoulder
    elbow
    wrist

No limits are guessed for base, roll, or gripper.
"""

import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIMITS_FILE = REPO_ROOT / "runtime/core/calibration/joint_limits.json"

JOINT_NAME_TO_ID = {
    "shoulder": "2",
    "elbow": "3",
    "wrist": "4",
}


class ValidationError(Exception):
    """Raised when the authoritative calibration data is unusable."""


def load_verified_limits():
    """
    Load Milestone 02 human-verified joint limits.

    The calibration file itself is authoritative.
    Values are not duplicated or adjusted here.
    """
    with LIMITS_FILE.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    limits = {}

    for joint_name, joint_id in JOINT_NAME_TO_ID.items():
        if joint_id not in raw:
            raise ValidationError(
                f"Authoritative limit missing for {joint_name} (joint {joint_id})"
            )

        entry = raw[joint_id]

        if entry.get("verified_by") != "human":
            raise ValidationError(
                f"{joint_name} limit is not marked human-verified"
            )

        negative = entry.get("negative_limit")
        positive = entry.get("positive_limit")

        if not isinstance(negative, (int, float)):
            raise ValidationError(
                f"{joint_name} negative_limit is not numeric"
            )

        if not isinstance(positive, (int, float)):
            raise ValidationError(
                f"{joint_name} positive_limit is not numeric"
            )

        if negative >= positive:
            raise ValidationError(
                f"{joint_name} calibration range is invalid"
            )

        limits[joint_name] = {
            "joint_id": joint_id,
            "negative_limit": float(negative),
            "positive_limit": float(positive),
            "units": entry.get("units", "radians"),
            "verified_by": entry.get("verified_by"),
            "milestone": entry.get("milestone"),
        }

    return limits


def validate_joint_proposal(proposal):
    """
    Validate a hypothetical joint target.

    Example:
        {
            "shoulder": 0.4,
            "elbow": 1.2,
            "wrist": 0.0
        }

    Returns an ALLOW/REJECT decision only.
    NO robot command is ever generated or transmitted.
    """

    result = {
        "allowed": False,
        "decision": "REJECT",
        "reasons": [],
        "checked_targets": {},
        "hardware_action": "NONE",
    }

    if not isinstance(proposal, dict):
        result["reasons"].append("proposal must be a JSON object/dictionary")
        return result

    if not proposal:
        result["reasons"].append("proposal contains no joint targets")
        return result

    limits = load_verified_limits()

    for joint_name, target in proposal.items():

        if joint_name not in JOINT_NAME_TO_ID:
            result["reasons"].append(
                f"{joint_name}: no human-verified Session/Milestone 02 "
                "limit is authorized for this validator"
            )
            continue

        if isinstance(target, bool) or not isinstance(target, (int, float)):
            result["reasons"].append(
                f"{joint_name}: target must be a numeric radian value"
            )
            continue

        target = float(target)

        if not math.isfinite(target):
            result["reasons"].append(
                f"{joint_name}: target must be finite"
            )
            continue

        limit = limits[joint_name]
        low = limit["negative_limit"]
        high = limit["positive_limit"]

        result["checked_targets"][joint_name] = {
            "target": target,
            "negative_limit": low,
            "positive_limit": high,
            "units": limit["units"],
        }

        if target < low:
            result["reasons"].append(
                f"{joint_name}: {target:.6f} rad is below "
                f"verified limit {low:.6f} rad"
            )

        elif target > high:
            result["reasons"].append(
                f"{joint_name}: {target:.6f} rad is above "
                f"verified limit {high:.6f} rad"
            )

    if not result["reasons"]:
        result["allowed"] = True
        result["decision"] = "ALLOW"

    return result


def run_self_test():
    tests = [
        (
            "SAFE TARGET",
            {
                "shoulder": 0.4,
                "elbow": 1.6,
                "wrist": 0.2,
            },
        ),
        (
            "SHOULDER TOO HIGH",
            {
                "shoulder": 1.25,
            },
        ),
        (
            "ELBOW TOO LOW",
            {
                "elbow": -0.5,
            },
        ),
        (
            "UNVERIFIED BASE",
            {
                "base": 0.2,
            },
        ),
    ]

    print("=== READ-ONLY MOTION VALIDATOR SELF-TEST ===")
    print(f"Calibration source: {LIMITS_FILE}")
    print("Hardware access: NONE")
    print()

    for name, proposal in tests:
        print(f"--- {name} ---")
        print("Proposal:")
        print(json.dumps(proposal, indent=2))
        print("Result:")
        print(json.dumps(validate_joint_proposal(proposal), indent=2))
        print()


if __name__ == "__main__":
    run_self_test()
