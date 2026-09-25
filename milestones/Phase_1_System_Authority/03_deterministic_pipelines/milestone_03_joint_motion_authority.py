"""Compatibility wrapper for the production one-shot motion authority.

Human-verified Milestone 02 limits remain authoritative and are enforced by
LocalMotionAuthority for shoulder, elbow, and wrist.
"""
import argparse
import json

from runtime.core.safety.production_motion import execute_joint


def arm_constrained_joint_motion():
    return {
        "armed": False,
        "reason": "LOCAL_PERMIT_ISSUED_DURING_EXECUTION",
        "sha256": None,
    }


def execute_constrained_joint_move(joint, target_rad):
    return execute_joint(joint, float(target_rad))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("joint")
    parser.add_argument("target_rad", type=float)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            execute_constrained_joint_move(args.joint, args.target_rad),
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
