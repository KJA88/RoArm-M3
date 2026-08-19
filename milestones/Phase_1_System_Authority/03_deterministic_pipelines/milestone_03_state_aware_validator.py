#!/usr/bin/env python3
"""
Milestone 03 — State-Aware Dry-Run Motion Proposal Validator

PURPOSE
-------
Combine the existing deterministic RoArm state reader with the existing
human-verified joint-limit validator.

This module is DRY-RUN ONLY.

It may:
- issue the existing read-only T:105 state query through get_feedback()
- inspect current joint state
- validate hypothetical shoulder/elbow/wrist targets against authoritative
  Milestone 02 joint limits
- calculate informational target deltas

It does NOT:
- enable torque
- send motion commands
- change controller mode
- modify robot state
- authorize hardware motion

IMPORTANT
---------
No authoritative maximum joint-step / delta limits currently exist.
Therefore calculated deltas are INFORMATIONAL ONLY and do not affect the
ALLOW/REJECT decision.

Hardware action is always NONE.
"""

from __future__ import annotations

import math
from typing import Any

from milestone_03_state_reader import get_feedback
from milestone_03_motion_validator import validate_joint_proposal


SUPPORTED_JOINTS = ("shoulder", "elbow", "wrist")


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _read_current_state() -> dict:
    """
    Perform exactly one state-reader call.

    A successful return from get_feedback() represents feedback obtained
    during this dry-run request. If the reader itself provides a 'fresh'
    field, that field is honored.
    """
    try:
        feedback = get_feedback()
    except Exception as exc:
        return {
            "connected": False,
            "fresh": False,
            "feedback": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    if not isinstance(feedback, dict):
        return {
            "connected": False,
            "fresh": False,
            "feedback": None,
            "error": "State reader returned a non-dictionary result",
        }

    # If get_feedback() explicitly reports connection/freshness, honor it.
    # Otherwise, successful completion of this immediate T:105 query is
    # treated as fresh feedback for this dry-run invocation.
    connected = feedback.get("connected", True)
    fresh = feedback.get("fresh", True)

    if connected is not True:
        return {
            "connected": False,
            "fresh": False,
            "feedback": feedback,
            "error": feedback.get("error", "State reader reported disconnected"),
        }

    if fresh is not True:
        return {
            "connected": True,
            "fresh": False,
            "feedback": feedback,
            "error": feedback.get("error", "State reader reported stale feedback"),
        }

    return {
        "connected": True,
        "fresh": True,
        "feedback": feedback,
        "error": None,
    }


def _extract_joints(feedback: dict) -> dict:
    joints = feedback.get("joints")

    if isinstance(joints, dict):
        return joints

    # Defensive fallback in case get_feedback() returns the normalized
    # joint values at the top level rather than beneath "joints".
    possible = {}
    for name in ("base", "shoulder", "elbow", "wrist", "roll", "gripper"):
        if name in feedback:
            possible[name] = feedback[name]

    return possible


def _calculate_deltas(proposal: dict, current_joints: dict) -> dict:
    """
    Calculate target-current deltas for information only.

    These values are NOT safety limits and do NOT affect the decision.
    """
    deltas = {}

    for joint in SUPPORTED_JOINTS:
        if joint not in proposal:
            continue

        target = proposal[joint]
        current = current_joints.get(joint)

        if _finite_number(target) and _finite_number(current):
            deltas[joint] = {
                "current": float(current),
                "target": float(target),
                "delta": float(target) - float(current),
                "units": "radians",
                "decision_authority": False,
            }

    return deltas


def validate_state_aware_joint_proposal(proposal: dict) -> dict:
    """
    State-aware dry-run validation.

    Decision sequence:
      1. Acquire current RoArm feedback.
      2. Require successful/fresh feedback.
      3. Run the existing authoritative absolute joint-limit validator.
      4. Report current-to-target deltas as informational only.

    No hardware motion is ever performed.
    """

    state = _read_current_state()

    if not state["connected"]:
        return {
            "allowed": False,
            "decision": "REJECT",
            "reasons": [
                f"Current RoArm state unavailable: {state['error']}"
            ],
            "state_gate": {
                "connected": False,
                "fresh": False,
            },
            "current_joints": {},
            "target_deltas": {},
            "limit_validation": None,
            "hardware_action": "NONE",
        }

    if not state["fresh"]:
        return {
            "allowed": False,
            "decision": "REJECT",
            "reasons": [
                f"Current RoArm state is not fresh: {state['error']}"
            ],
            "state_gate": {
                "connected": True,
                "fresh": False,
            },
            "current_joints": {},
            "target_deltas": {},
            "limit_validation": None,
            "hardware_action": "NONE",
        }

    feedback = state["feedback"]
    current_joints = _extract_joints(feedback)

    # Require readable current state for every proposed authoritative joint.
    state_reasons = []
    for joint in SUPPORTED_JOINTS:
        if joint not in proposal:
            continue

        current = current_joints.get(joint)

        if not _finite_number(current):
            state_reasons.append(
                f"{joint}: current joint state is unavailable or invalid"
            )

    if state_reasons:
        return {
            "allowed": False,
            "decision": "REJECT",
            "reasons": state_reasons,
            "state_gate": {
                "connected": True,
                "fresh": True,
            },
            "current_joints": current_joints,
            "target_deltas": {},
            "limit_validation": None,
            "hardware_action": "NONE",
        }

    limit_result = validate_joint_proposal(proposal)

    deltas = _calculate_deltas(proposal, current_joints)

    reasons = list(limit_result.get("reasons", []))

    return {
        "allowed": bool(limit_result.get("allowed", False)),
        "decision": limit_result.get("decision", "REJECT"),
        "reasons": reasons,
        "state_gate": {
            "connected": True,
            "fresh": True,
        },
        "current_joints": {
            joint: current_joints[joint]
            for joint in SUPPORTED_JOINTS
            if joint in current_joints
        },
        "target_deltas": deltas,
        "delta_policy": (
            "INFORMATIONAL_ONLY: no human-verified maximum joint-step "
            "limits currently exist"
        ),
        "limit_validation": limit_result,
        "hardware_action": "NONE",
    }


if __name__ == "__main__":
    print("=== STATE-AWARE DRY-RUN: SAFE ABSOLUTE TARGET ===")
    print(
        validate_state_aware_joint_proposal(
            {
                "shoulder": 0.4,
                "elbow": 1.6,
                "wrist": 0.2,
            }
        )
    )

    print()
    print("=== STATE-AWARE DRY-RUN: OUT-OF-LIMIT TARGET ===")
    print(
        validate_state_aware_joint_proposal(
            {
                "shoulder": 1.25,
            }
        )
    )
