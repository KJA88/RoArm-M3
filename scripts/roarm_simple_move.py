#!/usr/bin/env python3
"""Daily-use CLI routed through the production one-shot authority."""
import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.core.safety.production_motion import (  # noqa: E402
    deny_unsupported,
    execute_joint,
)


def request_joint(joint, target):
    return execute_joint(joint, target)


def request_xyz(x, y, z):
    return deny_unsupported(
        "goto_xyz",
        reason="TASK_SPACE_POLICY_UNVERIFIED",
        requested_target={"x": x, "y": y, "z": z},
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    joint_parser = subparsers.add_parser("joint")
    joint_parser.add_argument("joint", choices=("shoulder", "elbow", "wrist"))
    joint_parser.add_argument("target", type=float)

    xyz_parser = subparsers.add_parser("goto_xyz")
    xyz_parser.add_argument("x", type=float)
    xyz_parser.add_argument("y", type=float)
    xyz_parser.add_argument("z", type=float)

    args = parser.parse_args(argv)
    if args.command == "joint":
        result = request_joint(args.joint, args.target)
    else:
        result = request_xyz(args.x, args.y, args.z)
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
