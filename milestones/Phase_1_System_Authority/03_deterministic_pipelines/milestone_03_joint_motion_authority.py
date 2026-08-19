#!/usr/bin/env python3

"""
Milestone 03 - Constrained Single-Joint Motion Authority V1

LIVE MOTION SCOPE
-----------------
This authority permits exactly ONE joint target per authorized execution.

Allowed joints:
    shoulder
    elbow
    wrist

Not authorized:
    base
    roll
    hand / gripper
    multiple joints in one call
    arbitrary serial commands
    arbitrary Cartesian commands

SAFETY / AUTHORITY CHAIN
------------------------
1. Validate requested joint name and target.
2. Run the existing state-aware joint proposal validator.
3. Require connected/fresh controller state through that validator.
4. Enforce existing human-verified Milestone 02 joint limits.
5. Require a local, short-lived, one-shot operator permit.
6. Verify this authority module has not changed since arming.
7. Acquire the shared exclusive motion lock.
8. Consume the permit BEFORE torque/motion commands.
9. Enable torque using the established T:210 command.
10. Send a PARTIAL T:102 command containing only the authorized joint.
11. Read final state and append to the shared motion audit log.

The partial T:102 pattern is taken directly from the authoritative
Milestone 02 joint-limit calibration implementation.

No new mechanical joint limits, step limits, delta limits, velocity limits,
workspace limits, or collision limits are invented here.
"""

import fcntl
import hashlib
import json
import math
import time
from pathlib import Path

import serial

from milestone_03_state_aware_validator import (
    validate_state_aware_joint_proposal,
)
from milestone_03_state_reader import get_feedback


REPO_ROOT = Path("/home/KA_PI/robotics/roarm-m3")

THIS_FILE = Path(__file__).resolve()

RUNTIME_DIR = Path("/home/KA_PI/roarm-mcp/runtime")
AUTH_FILE = RUNTIME_DIR / "constrained_joint_authority.json"
LOCK_FILE = RUNTIME_DIR / "motion.lock"
AUDIT_LOG = RUNTIME_DIR / "motion_audit.jsonl"

AUTH_MAX_AGE_SECONDS = 120

SERIAL_PORTS = (
    "/dev/serial/by-id/"
    "usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_"
    "5c6dc8363f01f01180d7c1295c2a50c9-if00-port0",
    "/dev/ttyUSB0",
)

BAUD = 115200

ALLOWED_JOINTS = {
    "shoulder",
    "elbow",
    "wrist",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(event: str, **fields) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp_unix": time.time(),
        "event": event,
        **fields,
    }

    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _serial_port() -> str:
    for port in SERIAL_PORTS:
        if Path(port).exists():
            return port

    raise RuntimeError(
        "RoArm serial device not found at stable by-id path or /dev/ttyUSB0"
    )


def arm_constrained_joint_motion() -> dict:
    """
    LOCAL OPERATOR ACTION ONLY.

    Arms exactly one future constrained single-joint motion.

    The target itself is still selected by the MCP caller, but the caller
    cannot exceed the state-aware validator's existing authority.
    """

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    digest = _sha256(THIS_FILE)

    permit = {
        "scope": "ONE_CONSTRAINED_SINGLE_JOINT_MOVE",
        "timestamp_unix": time.time(),
        "authority_file": str(THIS_FILE),
        "sha256": digest,
        "authority": "LOCAL_OPERATOR_ONE_SHOT",
        "max_age_seconds": AUTH_MAX_AGE_SECONDS,
    }

    AUTH_FILE.write_text(
        json.dumps(permit, indent=2),
        encoding="utf-8",
    )
    AUTH_FILE.chmod(0o600)

    _audit(
        "AUTHORIZATION_ARMED",
        routine="constrained_single_joint",
        scope=permit["scope"],
        sha256=digest,
        max_age_seconds=AUTH_MAX_AGE_SECONDS,
    )

    return permit


def _validate_input(joint, target_rad):
    if joint not in ALLOWED_JOINTS:
        return {
            "ok": False,
            "error": (
                "Joint must be exactly one of: "
                "shoulder, elbow, wrist."
            ),
        }

    if isinstance(target_rad, bool):
        return {
            "ok": False,
            "error": "target_rad must be a finite numeric value.",
        }

    try:
        value = float(target_rad)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "target_rad must be a finite numeric value.",
        }

    if not math.isfinite(value):
        return {
            "ok": False,
            "error": "target_rad must be finite.",
        }

    return {
        "ok": True,
        "joint": joint,
        "target_rad": value,
    }


def _check_local_permit():
    try:
        permit = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None, (
            "Local constrained-joint authorization is not armed. "
            "Operator must run roarm-arm-joints on the Raspberry Pi."
        )

    if permit.get("scope") != "ONE_CONSTRAINED_SINGLE_JOINT_MOVE":
        AUTH_FILE.unlink(missing_ok=True)
        return None, "Local motion authorization scope is invalid."

    try:
        age = time.time() - float(permit["timestamp_unix"])
    except Exception:
        age = AUTH_MAX_AGE_SECONDS + 1

    if age < 0 or age > AUTH_MAX_AGE_SECONDS:
        AUTH_FILE.unlink(missing_ok=True)
        return None, "Local constrained-joint authorization expired."

    current_hash = _sha256(THIS_FILE)

    if permit.get("sha256") != current_hash:
        AUTH_FILE.unlink(missing_ok=True)
        return None, (
            "Joint-motion authority code changed after local authorization."
        )

    return permit, None


def execute_constrained_joint_move(joint: str, target_rad: float) -> dict:
    """
    Execute one validated partial T:102 joint command.

    Exactly one of shoulder/elbow/wrist may be targeted.
    """

    parsed = _validate_input(joint, target_rad)

    if not parsed["ok"]:
        return {
            "ok": False,
            "authorized": False,
            "error": parsed["error"],
            "hardware_action": "NONE",
        }

    joint = parsed["joint"]
    target_rad = parsed["target_rad"]

    # ---------------------------------------------------------
    # Existing deterministic / state-aware validation authority.
    # ---------------------------------------------------------

    proposal = {
        joint: target_rad,
    }

    validation = validate_state_aware_joint_proposal(proposal)

    if not validation.get("allowed", False):
        _audit(
            "MOTION_REJECTED",
            routine="constrained_single_joint",
            joint=joint,
            target_rad=target_rad,
            reason="state_aware_validator_rejected",
            validation=validation,
        )

        return {
            "ok": False,
            "authorized": False,
            "joint": joint,
            "target_rad": target_rad,
            "validation": validation,
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # Require local one-shot operator authorization.
    # ---------------------------------------------------------

    permit, permit_error = _check_local_permit()

    if permit is None:
        _audit(
            "MOTION_REJECTED",
            routine="constrained_single_joint",
            joint=joint,
            target_rad=target_rad,
            reason=permit_error,
        )

        return {
            "ok": False,
            "authorized": False,
            "joint": joint,
            "target_rad": target_rad,
            "validation": validation,
            "error": permit_error,
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # Shared exclusive hardware motion lock.
    # ---------------------------------------------------------

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK_FILE.open("w")

    try:
        fcntl.flock(
            lock_handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        lock_handle.close()

        return {
            "ok": False,
            "authorized": False,
            "joint": joint,
            "target_rad": target_rad,
            "error": "Another RoArm motion routine is already active.",
            "hardware_action": "NONE",
        }

    try:
        # -----------------------------------------------------
        # Consume permit BEFORE any hardware-changing command.
        # -----------------------------------------------------

        AUTH_FILE.unlink(missing_ok=True)

        authority_hash = _sha256(THIS_FILE)

        _audit(
            "MOTION_AUTHORIZATION_CONSUMED",
            routine="constrained_single_joint",
            joint=joint,
            target_rad=target_rad,
            sha256=authority_hash,
        )

        # -----------------------------------------------------
        # Hardware control.
        #
        # Mirrors Milestone 02's proven partial T:102 pattern:
        # only the selected joint is included in the command.
        # -----------------------------------------------------

        port = _serial_port()

        ser = serial.Serial(
            port=port,
            baudrate=BAUD,
            timeout=1,
        )

        try:
            ser.setRTS(False)
            ser.setDTR(False)
            time.sleep(0.2)

            torque_cmd = {
                "T": 210,
                "cmd": 1,
            }

            ser.write(
                (json.dumps(torque_cmd) + "\n").encode("ascii")
            )
            ser.flush()

            time.sleep(0.5)

            move_cmd = {
                "T": 102,
                joint: target_rad,
                "spd": 0,
                "acc": 0,
            }

            _audit(
                "MOTION_STARTED",
                routine="constrained_single_joint",
                joint=joint,
                target_rad=target_rad,
                command=move_cmd,
            )

            ser.write(
                (json.dumps(move_cmd) + "\n").encode("ascii")
            )
            ser.flush()

            time.sleep(2.0)

        finally:
            ser.close()

        final_state = get_feedback()

        _audit(
            "MOTION_FINISHED",
            routine="constrained_single_joint",
            joint=joint,
            target_rad=target_rad,
            final_state=final_state,
        )

        return {
            "ok": True,
            "authorized": True,
            "authorization": "LOCAL_ONE_SHOT_CONSUMED",
            "routine": "CONSTRAINED_SINGLE_JOINT",
            "joint": joint,
            "target_rad": target_rad,
            "validation": validation,
            "final_state": final_state,
            "hardware_action": "CONSTRAINED_JOINT_MOVE_EXECUTED",
        }

    except Exception as exc:
        _audit(
            "MOTION_FAILED",
            routine="constrained_single_joint",
            joint=joint,
            target_rad=target_rad,
            error=str(exc),
        )

        return {
            "ok": False,
            "authorized": True,
            "joint": joint,
            "target_rad": target_rad,
            "error": str(exc),
            "hardware_action": "MOTION_ATTEMPT_FAILED",
        }

    finally:
        try:
            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_UN,
            )
        finally:
            lock_handle.close()


if __name__ == "__main__":
    permit = arm_constrained_joint_motion()

    print()
    print("RoArm constrained joint motion ARMED")
    print("Authority: LOCAL OPERATOR / ONE USE")
    print("Scope: ONE shoulder/elbow/wrist target")
    print(f"Expires: {AUTH_MAX_AGE_SECONDS} seconds")
    print(f"Authority SHA-256: {permit['sha256']}")
    print()
    print(
        "The next valid move_constrained_joint call may execute "
        "one physical joint movement."
    )
