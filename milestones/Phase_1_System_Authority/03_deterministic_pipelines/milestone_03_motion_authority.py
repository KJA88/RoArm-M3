#!/usr/bin/env python3

"""
Milestone 03 - RoArm Motion Authority V1

PURPOSE
-------
Provide a narrow, machine-verifiable authority boundary for approved
live RoArm motion.

CURRENT APPROVED LIVE MOTION
----------------------------
- Lissajous / 3D figure-8 routine only.

NOT AUTHORIZED
--------------
- Arbitrary joint motion
- Arbitrary Cartesian motion
- Arbitrary torque control
- Arbitrary gripper control
- User-supplied trajectories
- User-supplied serial commands

AUTHORIZATION MODEL
-------------------
A live Lissajous motion requires:

1. Fresh, connected T:105 controller feedback.
2. Exact approved routine name.
3. Local one-shot operator authorization.
4. Authorization age <= 120 seconds.
5. SHA-256 match between authorization and the exact script executed.
6. Exclusive motion lock.
7. Authorization is consumed BEFORE physical motion begins.
8. Motion attempt/result is logged.

Historical read-only Phase 1 tools remain read-only.
This module is the explicit authority boundary for approved live motion.
"""

import fcntl
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path("/home/KA_PI/robotics/roarm-m3")

STATE_DIR = (
    REPO_ROOT
    / "milestones/Phase_1_System_Authority/03_deterministic_pipelines"
)

LISSAJOUS_SCRIPT = (
    REPO_ROOT
    / "lessons/01_trajectory_and_gripper/demo_lissajous.py"
)


CANDLE_SCRIPT = (
    REPO_ROOT
    / "lessons/01_trajectory_and_gripper/demo_candle.py"
)


RUNTIME_DIR = Path("/home/KA_PI/robotics/roarm-m3/mcp/runtime")
CANDLE_AUTH_FILE = RUNTIME_DIR / "candle_authority.json"
AUTH_FILE = RUNTIME_DIR / "lissajous_authority.json"
LOCK_FILE = RUNTIME_DIR / "motion.lock"
AUDIT_LOG = RUNTIME_DIR / "motion_audit.jsonl"

AUTH_MAX_AGE_SECONDS = 120
MOTION_TIMEOUT_SECONDS = 45

sys.path.insert(0, str(STATE_DIR))

from milestone_03_state_reader import get_feedback


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


def arm_lissajous() -> dict:
    """
    LOCAL OPERATOR ACTION.

    Creates one short-lived authorization for the exact current
    Lissajous script.
    """

    if not LISSAJOUS_SCRIPT.is_file():
        raise FileNotFoundError(
            f"Approved Lissajous script not found: {LISSAJOUS_SCRIPT}"
        )

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    digest = _sha256(LISSAJOUS_SCRIPT)

    permit = {
        "routine": "lissajous",
        "timestamp_unix": time.time(),
        "script": str(LISSAJOUS_SCRIPT),
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
        routine="lissajous",
        sha256=digest,
        max_age_seconds=AUTH_MAX_AGE_SECONDS,
    )

    return permit



def arm_candle() -> dict:
    """
    LOCAL OPERATOR ACTION.

    Creates one short-lived, one-use authorization for the exact
    fixed Candle routine.
    """

    if not CANDLE_SCRIPT.is_file():
        raise FileNotFoundError(
            f"Approved Candle script not found: {CANDLE_SCRIPT}"
        )

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    digest = _sha256(CANDLE_SCRIPT)

    permit = {
        "routine": "candle",
        "timestamp_unix": time.time(),
        "script": str(CANDLE_SCRIPT),
        "sha256": digest,
        "authority": "LOCAL_OPERATOR_ONE_SHOT",
        "max_age_seconds": AUTH_MAX_AGE_SECONDS,
    }

    CANDLE_AUTH_FILE.write_text(
        json.dumps(permit, indent=2),
        encoding="utf-8",
    )

    CANDLE_AUTH_FILE.chmod(0o600)

    _audit(
        "AUTHORIZATION_ARMED",
        routine="candle",
        sha256=digest,
        max_age_seconds=AUTH_MAX_AGE_SECONDS,
    )

    return permit

def _read_fresh_state() -> dict:
    try:
        state = get_feedback()
    except Exception as exc:
        return {
            "connected": False,
            "fresh": False,
            "error": str(exc),
        }

    return state


def execute_lissajous() -> dict:
    """
    Execute the only currently approved live-motion routine.

    This function does not accept trajectory parameters.
    """

    if not LISSAJOUS_SCRIPT.is_file():
        return {
            "ok": False,
            "authorized": False,
            "error": "Approved Lissajous script is missing.",
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # 1. Require live controller state before motion authority.
    # ---------------------------------------------------------

    state = _read_fresh_state()

    if not state.get("connected"):
        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="controller_not_connected",
        )

        return {
            "ok": False,
            "authorized": False,
            "error": "RoArm controller is not connected.",
            "hardware_action": "NONE",
        }

    if not state.get("fresh"):
        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="controller_state_not_fresh",
        )

        return {
            "ok": False,
            "authorized": False,
            "error": "RoArm controller state is not fresh.",
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # 2. Require local one-shot authorization.
    # ---------------------------------------------------------

    try:
        permit = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="local_authorization_missing",
        )

        return {
            "ok": False,
            "authorized": False,
            "error": (
                "Local one-shot motion authorization is not armed. "
                "Operator must run roarm-arm-lissajous on the Raspberry Pi."
            ),
            "hardware_action": "NONE",
        }

    if permit.get("routine") != "lissajous":
        AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="wrong_authorization_routine",
        )

        return {
            "ok": False,
            "authorized": False,
            "error": "Authorization is not for the Lissajous routine.",
            "hardware_action": "NONE",
        }

    try:
        age = time.time() - float(permit["timestamp_unix"])
    except Exception:
        age = AUTH_MAX_AGE_SECONDS + 1

    if age < 0 or age > AUTH_MAX_AGE_SECONDS:
        AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="authorization_expired",
            age_seconds=age,
        )

        return {
            "ok": False,
            "authorized": False,
            "error": "Local motion authorization expired.",
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # 3. Verify exact script authorized by local operator.
    # ---------------------------------------------------------

    current_hash = _sha256(LISSAJOUS_SCRIPT)

    if permit.get("sha256") != current_hash:
        AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_REJECTED",
            routine="lissajous",
            reason="script_hash_changed",
            current_sha256=current_hash,
        )

        return {
            "ok": False,
            "authorized": False,
            "error": (
                "Lissajous script changed after local authorization. "
                "Re-arm locally before attempting motion."
            ),
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # 4. Exclusive hardware-motion lock.
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
            "error": "Another RoArm motion routine is already active.",
            "hardware_action": "NONE",
        }

    try:
        # -----------------------------------------------------
        # 5. Consume authorization BEFORE physical actuation.
        # -----------------------------------------------------

        AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_AUTHORIZATION_CONSUMED",
            routine="lissajous",
            sha256=current_hash,
        )

        _audit(
            "MOTION_STARTED",
            routine="lissajous",
            script=str(LISSAJOUS_SCRIPT),
            sha256=current_hash,
        )

        # -----------------------------------------------------
        # 6. Execute exact locally-authorized routine.
        # -----------------------------------------------------

        result = subprocess.run(
            [sys.executable, str(LISSAJOUS_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=MOTION_TIMEOUT_SECONDS,
            check=False,
        )

        final_state = _read_fresh_state()

        _audit(
            "MOTION_FINISHED",
            routine="lissajous",
            returncode=result.returncode,
            sha256=current_hash,
        )

        return {
            "ok": result.returncode == 0,
            "authorized": True,
            "authorization": "LOCAL_ONE_SHOT_CONSUMED",
            "routine": "3D_LISSAJOUS_FIGURE_8",
            "script": str(LISSAJOUS_SCRIPT),
            "verified_script_sha256": current_hash,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "final_state": final_state,
            "hardware_action": "LISSAJOUS_EXECUTED",
        }

    except subprocess.TimeoutExpired as exc:
        _audit(
            "MOTION_FAILED",
            routine="lissajous",
            reason="timeout",
        )

        return {
            "ok": False,
            "authorized": True,
            "error": (
                f"Lissajous routine exceeded "
                f"{MOTION_TIMEOUT_SECONDS}-second timeout."
            ),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "hardware_action": "MOTION_PROCESS_TERMINATED",
        }

    except Exception as exc:
        _audit(
            "MOTION_FAILED",
            routine="lissajous",
            reason=str(exc),
        )

        return {
            "ok": False,
            "authorized": True,
            "error": str(exc),
            "hardware_action": "MOTION_ATTEMPT_FAILED",
        }

    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()


def execute_candle() -> dict:
    """
    Execute the approved fixed joint-space Candle routine.

    No user-supplied motion parameters are accepted.
    """

    if not CANDLE_SCRIPT.is_file():
        return {
            "ok": False,
            "authorized": False,
            "error": "Approved Candle script is missing.",
            "hardware_action": "NONE",
        }

    state = _read_fresh_state()

    if not state.get("connected"):
        _audit(
            "MOTION_REJECTED",
            routine="candle",
            reason="controller_not_connected",
        )
        return {
            "ok": False,
            "authorized": False,
            "error": "RoArm controller is not connected.",
            "hardware_action": "NONE",
        }

    if not state.get("fresh"):
        _audit(
            "MOTION_REJECTED",
            routine="candle",
            reason="controller_state_not_fresh",
        )
        return {
            "ok": False,
            "authorized": False,
            "error": "RoArm controller state is not fresh.",
            "hardware_action": "NONE",
        }

    try:
        permit = json.loads(
            CANDLE_AUTH_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {
            "ok": False,
            "authorized": False,
            "error": (
                "Local one-shot Candle authorization is not armed. "
                "Operator must run roarm-arm-candle on the Raspberry Pi."
            ),
            "hardware_action": "NONE",
        }

    try:
        age = time.time() - float(permit["timestamp_unix"])
    except Exception:
        age = AUTH_MAX_AGE_SECONDS + 1

    if (
        permit.get("routine") != "candle"
        or age < 0
        or age > AUTH_MAX_AGE_SECONDS
    ):
        CANDLE_AUTH_FILE.unlink(missing_ok=True)
        return {
            "ok": False,
            "authorized": False,
            "error": "Local Candle authorization expired or is invalid.",
            "hardware_action": "NONE",
        }

    current_hash = _sha256(CANDLE_SCRIPT)

    if permit.get("sha256") != current_hash:
        CANDLE_AUTH_FILE.unlink(missing_ok=True)
        return {
            "ok": False,
            "authorized": False,
            "error": "Candle script changed after local authorization.",
            "hardware_action": "NONE",
        }

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
            "error": "Another RoArm motion routine is already active.",
            "hardware_action": "NONE",
        }

    try:
        # Consume permit BEFORE motion.
        CANDLE_AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_AUTHORIZATION_CONSUMED",
            routine="candle",
            sha256=current_hash,
        )

        _audit(
            "MOTION_STARTED",
            routine="candle",
            script=str(CANDLE_SCRIPT),
            sha256=current_hash,
        )

        result = subprocess.run(
            [sys.executable, str(CANDLE_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        final_state = _read_fresh_state()

        _audit(
            "MOTION_FINISHED",
            routine="candle",
            returncode=result.returncode,
            sha256=current_hash,
        )

        return {
            "ok": result.returncode == 0,
            "authorized": True,
            "authorization": "LOCAL_ONE_SHOT_CONSUMED",
            "routine": "CANDLE_HOME",
            "script": str(CANDLE_SCRIPT),
            "verified_script_sha256": current_hash,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "final_state": final_state,
            "hardware_action": "CANDLE_EXECUTED",
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "authorized": True,
            "error": "Candle routine timed out.",
            "hardware_action": "MOTION_PROCESS_TERMINATED",
        }

    except Exception as exc:
        return {
            "ok": False,
            "authorized": True,
            "error": str(exc),
            "hardware_action": "MOTION_ATTEMPT_FAILED",
        }

    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()


if __name__ == "__main__":
    permit = arm_lissajous()

    print("RoArm Lissajous motion ARMED")
    print("Authority: LOCAL OPERATOR / ONE USE")
    print(f"Expires: {AUTH_MAX_AGE_SECONDS} seconds")
    print(f"Script: {permit['script']}")
    print(f"SHA-256: {permit['sha256']}")
