#!/usr/bin/env python3

"""
Milestone 03 - Deterministic Read-Only RoArm State Reader

Purpose:
    Query the RoArm-M3-S for its current state without changing torque,
    commanding motion, or modifying robot configuration.

Protocol:
    Request:  {"T":105}
    Response: {"T":1051,...}

Safety:
    This module sends ONLY T=105.
    It does NOT send torque, joint, Cartesian, IK, gripper, or configuration
    commands.
"""

import json
import os
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.core.transport.roarm_http import (  # noqa: E402
    DEFAULT_HTTP_BASE_URL,
    RoArmHttpClient,
    normalize_feedback,
)


def get_feedback():
    """Perform one HTTP T=105 query and require a T=1051 response."""
    base_url = os.environ.get("ROARM_HTTP_BASE_URL", DEFAULT_HTTP_BASE_URL)
    transport = RoArmHttpClient(base_url)
    try:
        return normalize_feedback(
            transport.read_state(),
            base_url=base_url,
            now=time.time(),
        )

    finally:
        transport.close()


def main():
    try:
        state = get_feedback()

    except Exception as exc:
        state = {
            "connected": False,
            "fresh": False,
            "error": str(exc),
            "timestamp_unix": time.time(),
        }

    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
