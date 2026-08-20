#!/usr/bin/env python3
import fcntl, hashlib, json, time
from pathlib import Path
import serial

from milestone_03_state_reader import get_feedback

REPO_ROOT = Path("/home/KA_PI/robotics/roarm-m3")
THIS_FILE = Path(__file__).resolve()
RUNTIME_DIR = REPO_ROOT / "mcp/runtime"
AUTH_FILE = RUNTIME_DIR / "observe_left_authority.json"
LOCK_FILE = RUNTIME_DIR / "motion.lock"
AUDIT_LOG = RUNTIME_DIR / "motion_audit.jsonl"

AUTH_MAX_AGE_SECONDS = 120
BAUD = 115200

SERIAL_PORTS = (
    "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0",
    "/dev/ttyUSB0",
)

def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _audit(event, **fields):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp_unix": time.time(),
            "event": event,
            **fields
        }, sort_keys=True) + "\n")

def _port():
    for p in SERIAL_PORTS:
        if Path(p).exists():
            return p
    raise RuntimeError("RoArm serial device not found")

def arm_observe_left():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    permit = {
        "scope": "ONE_OBSERVE_LEFT_POSE",
        "timestamp_unix": time.time(),
        "authority_file": str(THIS_FILE),
        "sha256": _sha256(THIS_FILE),
        "authority": "LOCAL_OPERATOR_ONE_SHOT",
        "max_age_seconds": AUTH_MAX_AGE_SECONDS,
    }
    AUTH_FILE.write_text(json.dumps(permit, indent=2), encoding="utf-8")
    AUTH_FILE.chmod(0o600)
    _audit("AUTHORIZATION_ARMED",
           routine="observe_left",
           sha256=permit["sha256"])
    return permit

def execute_observe_left():
    state = get_feedback()
    if not state.get("connected") or not state.get("fresh"):
        return {
            "ok": False,
            "authorized": False,
            "error": "Controller state unavailable or stale",
            "hardware_action": "NONE"
        }

    try:
        permit = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "ok": False,
            "authorized": False,
            "error": "Local Observe Left authorization is not armed",
            "hardware_action": "NONE"
        }

    age = time.time() - float(permit.get("timestamp_unix", 0))
    if permit.get("scope") != "ONE_OBSERVE_LEFT_POSE" or age < 0 or age > AUTH_MAX_AGE_SECONDS:
        AUTH_FILE.unlink(missing_ok=True)
        return {
            "ok": False,
            "authorized": False,
            "error": "Observe Left authorization invalid or expired",
            "hardware_action": "NONE"
        }

    if permit.get("sha256") != _sha256(THIS_FILE):
        AUTH_FILE.unlink(missing_ok=True)
        return {
            "ok": False,
            "authorized": False,
            "error": "Observe Left authority code changed after arming",
            "hardware_action": "NONE"
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
            "hardware_action": "NONE"
        }

    try:
        AUTH_FILE.unlink(missing_ok=True)
        _audit("MOTION_AUTHORIZATION_CONSUMED",
               routine="observe_left")

        ser = serial.Serial(_port(), BAUD, timeout=1)
        try:
            ser.setRTS(False)
            ser.setDTR(False)
            time.sleep(0.2)

            cmd = {
                "T": 102,
                "base": 1.610679827,
                "shoulder": -0.832951568,
                "elbow": 2.411417799,
                "wrist": 0.006135923,
                "roll": 0.0,
                "hand": 3.152330519,
                "spd": 0,
                "acc": 0,
            }

            _audit("MOTION_STARTED",
                   routine="observe_left",
                   command=cmd)

            ser.write((json.dumps(cmd) + "\n").encode("ascii"))
            ser.flush()
            time.sleep(3.0)
        finally:
            ser.close()

        final_state = get_feedback()
        _audit("MOTION_FINISHED",
               routine="observe_left",
               final_state=final_state)

        return {
            "ok": True,
            "authorized": True,
            "authorization": "LOCAL_ONE_SHOT_CONSUMED",
            "routine": "OBSERVE_LEFT",
            "final_state": final_state,
            "hardware_action": "OBSERVE_LEFT_EXECUTED",
        }

    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
