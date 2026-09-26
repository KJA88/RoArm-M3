"""Pure, fail-closed motion-permit decisions."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Optional


DEFAULT_LIMITS_PATH = (
    Path(__file__).resolve().parents[1] / "calibration" / "joint_limits.json"
)

BASE_OPERATIONAL_MIN = -1.57
BASE_OPERATIONAL_MAX = 1.60
VERIFIED_JOINT_IDS = {"shoulder": "2", "elbow": "3", "wrist": "4"}
KNOWN_UNVERIFIED_JOINTS = {"roll", "gripper"}
KNOWN_JOINTS = (
    set(VERIFIED_JOINT_IDS) | KNOWN_UNVERIFIED_JOINTS | {"base"}
)


@dataclass
class MotionPermit:
    """One-shot authority for one exact local motion request."""

    permit_id: str
    issued_at: str
    expires_at: str
    allowed_action: str
    allowed_joint: str
    allowed_target: float
    max_delta: Optional[float]
    consumed: bool = False
    _authority_id: str = field(default="", repr=False, compare=False)

    def public_dict(self):
        result = asdict(self)
        result.pop("_authority_id", None)
        return result


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _timestamp(value):
    if _is_finite_number(value):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value.timestamp()
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return parsed.timestamp()
    raise ValueError("timestamp is not parseable")


def _stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _result(reason, checks):
    return {"allowed": reason == "PERMIT_OK", "reason": reason, "checks": checks}


def _load_limits(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("joint limits must be a JSON object")
    return value


def evaluate_motion_permit(
    *,
    current_state,
    target,
    guardian_state=None,
    limits_path=None,
    now=None,
    max_state_age_s=2.0,
):
    """Decide whether one requested single-joint move is locally safe."""
    checks = {"guardian_required": False}

    def deny(reason):
        return _result(reason, checks)

    if not isinstance(current_state, dict):
        return deny("STATE_MISSING")
    checks["state_present"] = True

    if current_state.get("connected") is not True:
        return deny("STATE_DISCONNECTED")
    checks["connected"] = True

    if current_state.get("fresh") is not True:
        return deny("STATE_NOT_FRESH")
    checks["fresh"] = True

    state_time = current_state.get("timestamp_unix")
    if state_time is None:
        state_time = current_state.get("observed_at")
    try:
        state_timestamp = _timestamp(state_time)
        current_timestamp = _timestamp(time.time() if now is None else now)
    except (TypeError, ValueError, OverflowError):
        return deny("STATE_TIMESTAMP_INVALID")
    if state_timestamp > current_timestamp:
        return deny("STATE_TIMESTAMP_INVALID")
    checks["timestamp_valid"] = True

    if not _is_finite_number(max_state_age_s) or max_state_age_s < 0:
        return deny("TARGET_INVALID")
    state_age = current_timestamp - state_timestamp
    checks["state_age_s"] = state_age
    if state_age > float(max_state_age_s):
        return deny("STATE_STALE")
    checks["state_age_valid"] = True

    if not isinstance(target, dict) or set(target) - {"joint", "target", "max_delta"}:
        return deny("TARGET_INVALID")
    joint = target.get("joint")
    target_value = target.get("target")
    if not isinstance(joint, str) or not joint or not _is_finite_number(target_value):
        return deny("TARGET_INVALID")
    checks["target_valid"] = True

    if joint not in KNOWN_JOINTS:
        return deny("UNKNOWN_JOINT")
    checks["joint_known"] = True
    if joint in KNOWN_UNVERIFIED_JOINTS:
        return deny("LIMIT_UNVERIFIED")

    if joint == "base":
        minimum = BASE_OPERATIONAL_MIN
        maximum = BASE_OPERATIONAL_MAX
        checks["verified_operational_bounds"] = {
            "joint_id": 1,
            "min": minimum,
            "max": maximum,
            "kind": "operational_not_mechanical",
        }
    else:
        try:
            path = DEFAULT_LIMITS_PATH if limits_path is None else limits_path
            limits = _load_limits(path)
        except (OSError, ValueError, TypeError):
            return deny("LIMITS_UNREADABLE")

        entry = limits.get(VERIFIED_JOINT_IDS[joint])
        if not isinstance(entry, dict):
            return deny("LIMIT_UNVERIFIED")
        minimum = entry.get("negative_limit")
        maximum = entry.get("positive_limit")
        if not (
            str(entry.get("name", "")).lower() == joint
            and entry.get("units") == "radians"
            and bool(entry.get("verified_by"))
            and _is_finite_number(minimum)
            and _is_finite_number(maximum)
            and minimum <= maximum
        ):
            return deny("LIMIT_UNVERIFIED")
        checks["limit_verified"] = True
        checks["verified_limit"] = {
            "joint_id": int(VERIFIED_JOINT_IDS[joint]),
            "min": float(minimum),
            "max": float(maximum),
        }

    if not minimum <= target_value <= maximum:
        return deny("TARGET_OUT_OF_LIMIT")
    checks[
        "target_in_operational_bounds" if joint == "base" else "target_in_limit"
    ] = True

    max_delta = target.get("max_delta")
    if max_delta is not None:
        if not _is_finite_number(max_delta) or max_delta < 0:
            return deny("TARGET_INVALID")
        current_joints = current_state.get("joints")
        current_value = current_joints.get(joint) if isinstance(current_joints, dict) else None
        if not _is_finite_number(current_value):
            return deny("STATE_FIELD_INVALID")
        checks["max_delta_valid"] = abs(target_value - current_value) <= max_delta
        if not checks["max_delta_valid"]:
            return deny("MAX_DELTA_EXCEEDED")

    if guardian_state is not None:
        checks["guardian_ignored"] = True
    return _result("PERMIT_OK", checks)


__all__ = [
    "BASE_OPERATIONAL_MAX",
    "BASE_OPERATIONAL_MIN",
    "DEFAULT_LIMITS_PATH",
    "MotionPermit",
    "evaluate_motion_permit",
    "_stamp",
    "_timestamp",
]
