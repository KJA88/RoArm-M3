#!/usr/bin/env python3

"""
Milestone 03 - Named Gripper Motion Authority V1

LIVE MOTION SCOPE
-----------------
This authority permits exactly ONE pre-approved gripper target
per authorized execution.

Allowed positions:

    open   -> hand = 1.6
    light  -> hand = 2.0
    firm   -> hand = 2.4
    pinch  -> hand = 2.8

The caller NEVER supplies an arbitrary numeric hand value.

Not authorized:
    arbitrary hand/gripper values
    base
    shoulder
    elbow
    wrist
    roll
    multiple joints
    arbitrary serial commands
    arbitrary Cartesian commands

SAFETY / AUTHORITY CHAIN
------------------------
1. Validate requested named gripper position.
2. Translate the name locally to its fixed approved hand value.
3. Require readable controller state.
4. Require a local, short-lived, one-shot operator permit.
5. Verify this authority module has not changed since arming.
6. Acquire the shared exclusive motion lock.
7. Consume the permit BEFORE torque/motion commands.
8. Enable torque using established T:210.
9. Send T:101 direct-joint control to gripper Joint 6 only.
10. Read final controller state.
11. Append result to the shared motion audit log.

No arbitrary hand values are exposed to MCP.
"""

import fcntl
import hashlib
import json
import time
from pathlib import Path

import serial

from milestone_03_state_reader import get_feedback


THIS_FILE = Path(__file__).resolve()

RUNTIME_DIR = Path("/home/KA_PI/robotics/roarm-m3/mcp/runtime")

AUTH_FILE = RUNTIME_DIR / "gripper_authority.json"
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


# -------------------------------------------------------------
# Authoritative Milestone 02 gripper calibration.
# -------------------------------------------------------------

GRIPPER_MAP_FILE = Path(
    "/home/KA_PI/robotics/roarm-m3/"
    "runtime/core/calibration/gripper_map.json"
)


def _load_gripper_positions():
    """
    Load the human-verified Milestone 02 gripper presets.

    Fail closed if the calibration is missing, malformed,
    uses unexpected units, or contains presets outside the
    declared safe range.
    """

    try:
        with GRIPPER_MAP_FILE.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as exc:
        return None, (
            "Unable to read authoritative gripper calibration: "
            + str(exc)
        )

    gripper = raw.get("gripper")

    if not isinstance(gripper, dict):
        return None, "Gripper calibration structure is invalid."

    if gripper.get("units") != "radians":
        return None, "Gripper calibration units must be radians."

    try:
        safe_min = float(gripper["safe_min"])
        safe_max = float(gripper["safe_max"])
    except Exception:
        return None, "Gripper safe_min/safe_max are invalid."

    if safe_min > safe_max:
        return None, "Gripper safe range is invalid."

    presets = gripper.get("presets")

    if not isinstance(presets, dict):
        return None, "Gripper presets are missing or invalid."

    required = ("open", "light", "firm", "pinch")
    positions = {}

    for name in required:
        if name not in presets:
            return None, f"Required gripper preset missing: {name}"

        try:
            value = float(presets[name])
        except Exception:
            return None, f"Gripper preset {name} is not numeric."

        if not (safe_min <= value <= safe_max):
            return None, (
                f"Gripper preset {name}={value} is outside "
                f"safe range {safe_min}..{safe_max}."
            )

        positions[name] = value

    return positions, None


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


def arm_gripper_motion() -> dict:
    """
    LOCAL OPERATOR ACTION ONLY.

    Arms exactly one future named gripper movement.

    The AI/MCP caller may subsequently choose only:

        open
        light
        firm
        pinch

    It cannot provide the underlying numeric hand value.
    """

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    digest = _sha256(THIS_FILE)

    permit = {
        "scope": "ONE_NAMED_GRIPPER_MOVE",
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
        routine="named_gripper",
        scope=permit["scope"],
        sha256=digest,
        max_age_seconds=AUTH_MAX_AGE_SECONDS,
    )

    return permit


def _validate_position(position):
    if not isinstance(position, str):
        return {
            "ok": False,
            "error": (
                "Gripper position must be exactly one of: "
                "open, light, firm, pinch."
            ),
        }

    name = position.strip().lower()

    positions, calibration_error = _load_gripper_positions()

    if positions is None:
        return {
            "ok": False,
            "error": calibration_error,
        }

    if name not in positions:
        return {
            "ok": False,
            "error": (
                "Gripper position must be exactly one of: "
                "open, light, firm, pinch."
            ),
        }

    return {
        "ok": True,
        "position": name,
        "target_rad": positions[name],
    }


def _check_local_permit():
    try:
        permit = json.loads(
            AUTH_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return None, (
            "Local gripper authorization is not armed. "
            "Operator must arm gripper authority on the Raspberry Pi."
        )

    if permit.get("scope") != "ONE_NAMED_GRIPPER_MOVE":
        AUTH_FILE.unlink(missing_ok=True)

        return None, (
            "Local gripper authorization scope is invalid."
        )

    try:
        age = time.time() - float(
            permit["timestamp_unix"]
        )
    except Exception:
        age = AUTH_MAX_AGE_SECONDS + 1

    if age < 0 or age > AUTH_MAX_AGE_SECONDS:
        AUTH_FILE.unlink(missing_ok=True)

        return None, (
            "Local gripper authorization expired."
        )

    current_hash = _sha256(THIS_FILE)

    if permit.get("sha256") != current_hash:
        AUTH_FILE.unlink(missing_ok=True)

        return None, (
            "Gripper authority code changed after "
            "local authorization."
        )

    return permit, None


def execute_gripper_position(position: str) -> dict:
    """
    Execute one named, pre-approved gripper movement.

    MCP-facing input:
        open
        light
        firm
        pinch

    The underlying numeric hand target is selected locally.
    """

    parsed = _validate_position(position)

    if not parsed["ok"]:
        return {
            "ok": False,
            "authorized": False,
            "error": parsed["error"],
            "hardware_action": "NONE",
        }

    position = parsed["position"]
    target_rad = parsed["target_rad"]

    # ---------------------------------------------------------
    # Require controller feedback before considering motion.
    # This confirms that the state/telemetry path is alive.
    # ---------------------------------------------------------

    try:
        initial_state = get_feedback()
    except Exception as exc:
        _audit(
            "MOTION_REJECTED",
            routine="named_gripper",
            position=position,
            target_rad=target_rad,
            reason="controller_state_unavailable",
            error=str(exc),
        )

        return {
            "ok": False,
            "authorized": False,
            "position": position,
            "target_rad": target_rad,
            "error": (
                "Controller state unavailable: "
                + str(exc)
            ),
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # Require local one-shot operator authorization.
    # ---------------------------------------------------------

    permit, permit_error = _check_local_permit()

    if permit is None:
        _audit(
            "MOTION_REJECTED",
            routine="named_gripper",
            position=position,
            target_rad=target_rad,
            reason=permit_error,
        )

        return {
            "ok": False,
            "authorized": False,
            "position": position,
            "target_rad": target_rad,
            "initial_state": initial_state,
            "error": permit_error,
            "hardware_action": "NONE",
        }

    # ---------------------------------------------------------
    # Shared exclusive RoArm hardware motion lock.
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
            "position": position,
            "target_rad": target_rad,
            "error": (
                "Another RoArm motion routine "
                "is already active."
            ),
            "hardware_action": "NONE",
        }

    try:
        # -----------------------------------------------------
        # Consume permit BEFORE ANY hardware-changing command.
        # -----------------------------------------------------

        AUTH_FILE.unlink(missing_ok=True)

        authority_hash = _sha256(THIS_FILE)

        _audit(
            "MOTION_AUTHORIZATION_CONSUMED",
            routine="named_gripper",
            position=position,
            target_rad=target_rad,
            sha256=authority_hash,
        )

        # -----------------------------------------------------
        # Hardware control.
        #
        # Uses the proven direct-joint gripper command:
        #
        #   T:101, joint 6 = hand / gripper
        #
        # No other arm joint is included in this command.
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
                (
                    json.dumps(torque_cmd)
                    + "\n"
                ).encode("ascii")
            )

            ser.flush()

            time.sleep(0.5)

            move_cmd = {
                "T": 101,
                "joint": 6,
                "rad": target_rad,
                "spd": 50,
                "acc": 0,
            }

            _audit(
                "MOTION_STARTED",
                routine="named_gripper",
                position=position,
                target_rad=target_rad,
                command=move_cmd,
                initial_state=initial_state,
            )

            ser.write(
                (
                    json.dumps(move_cmd)
                    + "\n"
                ).encode("ascii")
            )

            ser.flush()

            time.sleep(2.0)

        finally:
            ser.close()

        final_state = get_feedback()

        _audit(
            "MOTION_FINISHED",
            routine="named_gripper",
            position=position,
            target_rad=target_rad,
            final_state=final_state,
        )

        return {
            "ok": True,
            "authorized": True,
            "authorization": (
                "LOCAL_ONE_SHOT_CONSUMED"
            ),
            "routine": "NAMED_GRIPPER",
            "position": position,
            "target_rad": target_rad,
            "initial_state": initial_state,
            "final_state": final_state,
            "hardware_action": (
                "NAMED_GRIPPER_MOVE_EXECUTED"
            ),
        }

    except Exception as exc:
        _audit(
            "MOTION_FAILED",
            routine="named_gripper",
            position=position,
            target_rad=target_rad,
            error=str(exc),
        )

        return {
            "ok": False,
            "authorized": True,
            "position": position,
            "target_rad": target_rad,
            "error": str(exc),
            "hardware_action": (
                "MOTION_ATTEMPT_FAILED"
            ),
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
    permit = arm_gripper_motion()

    print()
    print("RoArm named gripper motion ARMED")
    print("Authority: LOCAL OPERATOR / ONE USE")
    print("Scope: ONE named gripper target")
    print("Allowed: open, light, firm, pinch")
    print(f"Expires: {AUTH_MAX_AGE_SECONDS} seconds")
    print(f"Authority SHA-256: {permit['sha256']}")
    print()
    print(
        "The next valid execute_gripper_position call "
        "may execute one physical gripper movement."
    )
