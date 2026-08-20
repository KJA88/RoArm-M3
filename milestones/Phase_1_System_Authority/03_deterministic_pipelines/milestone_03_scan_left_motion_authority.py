#!/usr/bin/env python3
import fcntl
import hashlib
import json
import time
from pathlib import Path

import serial

from milestone_03_state_reader import get_feedback

REPO_ROOT = Path("/home/KA_PI/robotics/roarm-m3")
THIS_FILE = Path(__file__).resolve()

RUNTIME_DIR = REPO_ROOT / "mcp/runtime"
AUTH_FILE = RUNTIME_DIR / "scan_left_authority.json"
LOCK_FILE = RUNTIME_DIR / "motion.lock"
AUDIT_LOG = RUNTIME_DIR / "motion_audit.jsonl"

AUTH_MAX_AGE_SECONDS = 120
BAUD = 115200

SERIAL_PORTS = (
    "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0",
    "/dev/ttyUSB0",
)

# Physically verified READY pose.
READY = {
    "T": 102,
    "base": 0.001533981,
    "shoulder": -0.832951568,
    "elbow": 2.399145952,
    "wrist": 0.004601942,
    "roll": 0.0,
    "hand": 3.163068385,
    "spd": 0,
    "acc": 0,
}

# Physically verified OBSERVE_LEFT base target.
LEFT_BASE = 1.610679827

# Physically tested camera-pan motion profile.
SCAN_SPEED = 200
SCAN_ACCEL = 10


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(event, **fields):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp_unix": time.time(),
            "event": event,
            **fields,
        }, sort_keys=True) + "\n")


def _port():
    for p in SERIAL_PORTS:
        if Path(p).exists():
            return p

    raise RuntimeError("RoArm serial device not found")


def _send(ser, command):
    ser.write((json.dumps(command) + "\n").encode("ascii"))
    ser.flush()


def arm_scan_left():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    permit = {
        "scope": "ONE_SCAN_LEFT",
        "timestamp_unix": time.time(),
        "authority_file": str(THIS_FILE),
        "sha256": _sha256(THIS_FILE),
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
        routine="scan_left",
        sha256=permit["sha256"],
    )

    return permit


def execute_scan_left():
    state = get_feedback()

    if not state.get("connected") or not state.get("fresh"):
        return {
            "ok": False,
            "authorized": False,
            "error": "Controller state unavailable or stale",
            "hardware_action": "NONE",
        }

    try:
        permit = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "ok": False,
            "authorized": False,
            "error": "Local Scan Left authorization is not armed",
            "hardware_action": "NONE",
        }

    age = time.time() - float(permit.get("timestamp_unix", 0))

    if (
        permit.get("scope") != "ONE_SCAN_LEFT"
        or age < 0
        or age > AUTH_MAX_AGE_SECONDS
    ):
        AUTH_FILE.unlink(missing_ok=True)

        return {
            "ok": False,
            "authorized": False,
            "error": "Scan Left authorization invalid or expired",
            "hardware_action": "NONE",
        }

    if permit.get("sha256") != _sha256(THIS_FILE):
        AUTH_FILE.unlink(missing_ok=True)

        return {
            "ok": False,
            "authorized": False,
            "error": "Scan Left authority code changed after arming",
            "hardware_action": "NONE",
        }

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock = LOCK_FILE.open("w")

    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()

        return {
            "ok": False,
            "authorized": False,
            "error": "Another RoArm motion routine is active",
            "hardware_action": "NONE",
        }

    try:
        AUTH_FILE.unlink(missing_ok=True)

        _audit(
            "MOTION_AUTHORIZATION_CONSUMED",
            routine="scan_left",
        )

        ser = serial.Serial(_port(), BAUD, timeout=1)

        try:
            ser.setRTS(False)
            ser.setDTR(False)
            time.sleep(0.2)

            _send(ser, {"T": 210, "cmd": 1})

            # Establish the known Ready posture first.
            _audit("SCAN_STAGE", routine="scan_left", stage="READY")
            _send(ser, READY)
            time.sleep(3.0)

            # Then perform the proven smooth base-only camera pan.
            scan_cmd = {
                "T": 101,
                "joint": 1,
                "rad": LEFT_BASE,
                "spd": SCAN_SPEED,
                "acc": SCAN_ACCEL,
            }

            _audit(
                "MOTION_STARTED",
                routine="scan_left",
                command=scan_cmd,
            )

            _send(ser, scan_cmd)
            time.sleep(5.0)

        finally:
            ser.close()

        final_state = get_feedback()

        _audit(
            "MOTION_FINISHED",
            routine="scan_left",
            final_state=final_state,
        )

        return {
            "ok": True,
            "authorized": True,
            "authorization": "LOCAL_ONE_SHOT_CONSUMED",
            "routine": "SCAN_LEFT",
            "start_pose": "READY",
            "target": "OBSERVE_LEFT",
            "scan_speed": SCAN_SPEED,
            "scan_acceleration": SCAN_ACCEL,
            "final_state": final_state,
            "hardware_action": "SCAN_LEFT_EXECUTED",
        }

    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
