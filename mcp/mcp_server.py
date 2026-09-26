#!/usr/bin/env python3

"""
RoArm-M3 MCP Server

Current architecture:

- Existing state and validation tools remain read-only/dry-run.
- Motion intents route through the local one-shot production authority.
- Arbitrary hardware motion is not exposed.

Historical Phase 1 read-only language describes the earlier development
state and is not the current global server policy.
"""

import json
import sys
import threading
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings


REPO_ROOT = Path("/home/KA_PI/robotics/roarm-m3")

MILESTONE_03_DIR = (
    REPO_ROOT
    / "milestones/Phase_1_System_Authority/03_deterministic_pipelines"
)

JOINT_LIMITS_FILE = (
    REPO_ROOT
    / "runtime/core/calibration/joint_limits.json"
)

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(MILESTONE_03_DIR))

from milestone_03_state_reader import get_feedback
from milestone_03_motion_validator import validate_joint_proposal
from milestone_03_state_aware_validator import (
    validate_state_aware_joint_proposal,
)
from milestone_03_motion_authority import execute_lissajous
from milestone_03_candle_motion_authority import execute_candle
from milestone_03_joint_motion_authority import execute_constrained_joint_move
from milestone_03_gripper_motion_authority import execute_gripper_position
from milestone_03_home_motion_authority import execute_home
from milestone_03_ready_motion_authority import execute_ready
from milestone_03_observe_left_motion_authority import execute_observe_left
from milestone_03_observe_center_motion_authority import execute_observe_center
from milestone_03_observe_right_motion_authority import execute_observe_right
from milestone_03_scan_left_motion_authority import execute_scan_left
from milestone_03_scan_right_motion_authority import execute_scan_right


security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "127.0.0.1:*",
        "localhost:*",
        "[::1]:*",
        "roarm.syzygylab.net",
        "roarm.syzygylab.net:*",
    ],
    allowed_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
        "https://roarm.syzygylab.net",
    ],
)


mcp = MCPServer(
    "RoArm-M3",
    instructions=(
        "Current RoArm-M3 interface. Existing state-inspection and "
        "proposal-validation tools remain read-only. run_lissajous is "
        "the first intentionally approved live-motion tool and MUST pass "
        "through milestone_03_motion_authority.py. The motion authority "
        "requires fresh controller state plus a short-lived one-use "
        "authorization created locally by the operator. Remote AI clients "
        "cannot create that authorization. Arbitrary motion is not exposed."
    ),
)


_motion_lock = threading.Lock()


def query_state():
    try:
        return get_feedback()
    except Exception as exc:
        return {
            "connected": False,
            "fresh": False,
            "error": str(exc),
        }


@mcp.tool()
def get_roarm_status() -> dict:
    """
    Return the main read-only RoArm state summary.
    """

    state = query_state()

    if not state.get("connected"):
        return state

    return {
        "connected": state["connected"],
        "fresh": state["fresh"],
        "port": state["port"],
        "baud": state["baud"],
        "timestamp_unix": state["timestamp_unix"],
        "pose": state["pose"],
        "joints": state["joints"],
        "additional_feedback": state["additional_feedback"],
    }


@mcp.tool()
def get_current_pose() -> dict:
    """
    Return the current Cartesian pose from read-only state feedback.
    """

    state = query_state()

    if not state.get("connected"):
        return state

    return {
        "connected": True,
        "fresh": state["fresh"],
        "timestamp_unix": state["timestamp_unix"],
        "pose": state["pose"],
    }


@mcp.tool()
def get_joint_positions() -> dict:
    """
    Return the current joint positions from read-only state feedback.
    """

    state = query_state()

    if not state.get("connected"):
        return state

    return {
        "connected": True,
        "fresh": state["fresh"],
        "timestamp_unix": state["timestamp_unix"],
        "joints": state["joints"],
    }


@mcp.tool()
def get_joint_limits() -> dict:
    """
    Return the authoritative human-verified Milestone 02 joint limits.

    Only limits explicitly present in the authoritative calibration file
    are returned. No limits are inferred or invented.
    """

    try:
        with JOINT_LIMITS_FILE.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "source": str(JOINT_LIMITS_FILE),
            "hardware_action": "NONE",
        }

    limits = {}

    for joint_id, entry in raw.items():
        if not isinstance(entry, dict):
            continue

        name = entry.get("name")

        if not name:
            continue

        limits[name.lower()] = {
            "joint_id": joint_id,
            "negative_limit": entry.get("negative_limit"),
            "positive_limit": entry.get("positive_limit"),
            "units": entry.get("units"),
            "verified_by": entry.get("verified_by"),
            "milestone": entry.get("milestone"),
        }

    return {
        "ok": True,
        "authority": "Milestone 02 human-verified mechanical limits",
        "source": str(JOINT_LIMITS_FILE),
        "limits": limits,
        "note": (
            "Only joints with authoritative entries are reported. "
            "No base, roll, or gripper limits are inferred."
        ),
        "hardware_action": "NONE",
    }


@mcp.tool()
def get_controller_status() -> dict:
    """
    Return read-only controller communication status.

    This tool does NOT claim torque state because no authoritative
    read-only torque-state query has been established.
    """

    state = query_state()

    if not state.get("connected"):
        return {
            "controller_reachable": False,
            "connected": False,
            "fresh": False,
            "error": state.get("error", "RoArm controller unavailable"),
            "torque_status": "UNKNOWN_NOT_QUERIED",
            "hardware_action": "NONE",
        }

    return {
        "controller_reachable": True,
        "connected": True,
        "fresh": state.get("fresh", False),
        "port": state.get("port"),
        "baud": state.get("baud"),
        "timestamp_unix": state.get("timestamp_unix"),
        "protocol_query": "T:105",
        "protocol_response": "T:1051",
        "torque_status": "UNKNOWN_NOT_QUERIED",
        "note": (
            "Controller status means communication/read-feedback health. "
            "Torque state is deliberately not inferred."
        ),
        "hardware_action": "NONE",
    }


@mcp.tool()
def validate_roarm_joint_proposal(
    shoulder: float | None = None,
    elbow: float | None = None,
    wrist: float | None = None,
) -> dict:
    """
    Validate hypothetical joint targets against authoritative Milestone 02
    absolute limits.

    Pure software validation only.
    """

    proposal = {}

    if shoulder is not None:
        proposal["shoulder"] = shoulder

    if elbow is not None:
        proposal["elbow"] = elbow

    if wrist is not None:
        proposal["wrist"] = wrist

    return validate_joint_proposal(proposal)


@mcp.tool()
def validate_roarm_state_aware_joint_proposal(
    shoulder: float | None = None,
    elbow: float | None = None,
    wrist: float | None = None,
) -> dict:
    """
    Perform state-aware dry-run validation.

    Reads current RoArm feedback using T:105, validates against the
    authoritative Milestone 02 absolute limits, and reports deltas.

    hardware_action is always NONE.
    """

    proposal = {}

    if shoulder is not None:
        proposal["shoulder"] = shoulder

    if elbow is not None:
        proposal["elbow"] = elbow

    if wrist is not None:
        proposal["wrist"] = wrist

    return validate_state_aware_joint_proposal(proposal)


@mcp.tool()
def run_lissajous() -> dict:
    """
    Request the legacy Lissajous action through production authority.

    The adapter denies it until a verified trajectory policy exists.
    """

    return execute_lissajous()


@mcp.tool()
def scan_left() -> dict:
    """
    Request the fixed scan-left pose through local production authority.
    """
    return execute_scan_left()


@mcp.tool()
def scan_right() -> dict:
    """
    Request the fixed scan-right pose through local production authority.
    """
    return execute_scan_right()


@mcp.tool()
def move_observe_center() -> dict:
    """
    Request the fixed Observe Center pose through local production authority.
    """
    return execute_observe_center()


@mcp.tool()
def move_observe_right() -> dict:
    """
    Request the fixed Observe Right pose through local production authority.
    """
    return execute_observe_right()


@mcp.tool()
def move_observe_left() -> dict:
    """
    Request the fixed Observe Left pose through local production authority.
    """
    return execute_observe_left()


@mcp.tool()
def move_ready() -> dict:
    """
    Request the fixed Ready pose through local production authority.
    """
    return execute_ready()


@mcp.tool()
def move_home() -> dict:
    """
    Request Home through authority; denied until its policy is verified.
    """
    return execute_home()


@mcp.tool()
def move_to_candle() -> dict:
    """
    Request the fixed Candle pose through local production authority.
    """

    return execute_candle()


@mcp.tool()
def move_constrained_joint(
    joint: str,
    target_rad: float,
) -> dict:
    """
    Move exactly one approved RoArm joint to an absolute target in radians.

    LIVE HARDWARE ACTION.

    Allowed joint names:
    - shoulder
    - elbow
    - wrist

    The local adapter checks fresh state, verified limits, and an exact
    short-lived one-shot permit before execution.
    """

    return execute_constrained_joint_move(
        joint=joint,
        target_rad=target_rad,
    )


@mcp.tool()
def set_gripper(position: str) -> dict:
    """
    Request one named gripper position.

    Allowed values:
    - open
    - light
    - firm
    - pinch

    Arbitrary numeric gripper targets are not accepted.

    Each name routes through the local one-shot authority using the
    human-verified Milestone 02 calibration map.
    """

    return execute_gripper_position(position)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8040,
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
