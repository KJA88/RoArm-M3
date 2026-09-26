"""Fixed-purpose RoArm HTTP transport with no automatic retries."""
import json
import math
import time

import requests


DEFAULT_HTTP_BASE_URL = "http://192.168.4.1"
HTTP_TIMEOUT_S = 5.0
PRODUCTION_JOINTS = {"base", "shoulder", "elbow", "wrist"}
SCAN_BASE_ENDPOINTS = {1.610679827, -1.578466231}
VERIFIED_GRIPPER_PRESET_TARGETS = {1.6, 2.0, 2.4, 2.8}
ALL_STATE_JOINTS = {
    "base", "shoulder", "elbow", "wrist", "roll", "gripper"
}


class RoArmHttpError(RuntimeError):
    """RoArm HTTP response did not satisfy the fixed protocol."""


class RoArmHttpClient:
    """Shared HTTP request behavior for purpose-specific RoArm clients."""

    def __init__(
        self,
        base_url=DEFAULT_HTTP_BASE_URL,
        *,
        timeout_s=HTTP_TIMEOUT_S,
        session=None,
    ):
        self.base_url = str(base_url).rstrip("/")
        if not self.base_url:
            raise ValueError("RoArm HTTP base URL must not be empty")
        self.timeout_s = float(timeout_s)
        self._session = requests.Session() if session is None else session
        self._session.trust_env = False

    def _get(self, packet):
        command = json.dumps(packet, separators=(",", ":"))
        response = self._session.get(
            f"{self.base_url}/js?json={command}",
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        result = json.loads(response.text)
        if not isinstance(result, dict):
            raise RoArmHttpError("HTTP_RESPONSE_NOT_OBJECT")
        return result

    def read_state(self):
        return self._get({"T": 105})

    def close(self):
        close = getattr(self._session, "close", None)
        if close is not None:
            close()


class RoArmProductionHttpTransport(RoArmHttpClient):
    """HTTP execution surface limited to authorized production joints."""

    def move_joint(self, joint, target, *, current_joints):
        if joint not in PRODUCTION_JOINTS:
            raise RoArmHttpError("PRODUCTION_JOINT_NOT_SUPPORTED")
        if (
            not isinstance(target, (int, float))
            or isinstance(target, bool)
            or not math.isfinite(target)
        ):
            raise RoArmHttpError("PRODUCTION_TARGET_INVALID")
        if (
            not isinstance(current_joints, dict)
            or set(current_joints) != ALL_STATE_JOINTS
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in current_joints.values()
            )
        ):
            raise RoArmHttpError("PRESERVATION_STATE_INVALID")
        full_targets = dict(current_joints)
        full_targets[joint] = float(target)
        return self._get(
            {
                "T": 102,
                "base": float(full_targets["base"]),
                "shoulder": float(full_targets["shoulder"]),
                "elbow": float(full_targets["elbow"]),
                "wrist": float(full_targets["wrist"]),
                "roll": float(full_targets["roll"]),
                "hand": float(full_targets["gripper"]),
                "spd": 0,
                "acc": 0,
            }
        )

    def move_arm_pose(self, targets, *, roll, hand):
        if (
            not isinstance(targets, dict)
            or set(targets) != PRODUCTION_JOINTS
        ):
            raise RoArmHttpError("ARM_POSE_TARGETS_INVALID")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in (*targets.values(), roll, hand)
        ):
            raise RoArmHttpError("ARM_POSE_TARGET_INVALID")
        packet = {
            "T": 102,
            **{
                joint: float(targets[joint])
                for joint in ("base", "shoulder", "elbow", "wrist")
                if joint in targets
            },
            "roll": float(roll),
            "hand": float(hand),
            "spd": 0,
            "acc": 0,
        }
        return self._get(packet)

    def move_gripper_preset(self, target, *, current_joints):
        if (
            not isinstance(target, (int, float))
            or isinstance(target, bool)
            or not math.isfinite(target)
            or float(target) not in VERIFIED_GRIPPER_PRESET_TARGETS
        ):
            raise RoArmHttpError("GRIPPER_PRESET_NOT_AUTHORIZED")
        if (
            not isinstance(current_joints, dict)
            or set(current_joints) != ALL_STATE_JOINTS
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in current_joints.values()
            )
        ):
            raise RoArmHttpError("PRESERVATION_STATE_INVALID")
        return self._get(
            {
                "T": 102,
                "base": float(current_joints["base"]),
                "shoulder": float(current_joints["shoulder"]),
                "elbow": float(current_joints["elbow"]),
                "wrist": float(current_joints["wrist"]),
                "roll": float(current_joints["roll"]),
                "hand": float(target),
                "spd": 0,
                "acc": 0,
            }
        )

    def move_base_scan(self, target):
        if (
            not isinstance(target, (int, float))
            or isinstance(target, bool)
            or not math.isfinite(target)
            or float(target) not in SCAN_BASE_ENDPOINTS
        ):
            raise RoArmHttpError("SCAN_BASE_ENDPOINT_NOT_AUTHORIZED")
        return self._get(
            {
                "T": 101,
                "joint": 1,
                "rad": float(target),
                "spd": 200,
                "acc": 10,
            }
        )


def normalize_feedback(feedback, *, base_url=DEFAULT_HTTP_BASE_URL, now=None):
    """Convert one valid T=1051 packet to production state evidence."""
    if not isinstance(feedback, dict) or feedback.get("T") != 1051:
        raise RoArmHttpError("T105_READBACK_INVALID")
    timestamp = time.time() if now is None else float(now)
    return {
        "connected": True,
        "fresh": True,
        "transport": "http",
        "base_url": str(base_url).rstrip("/"),
        "port": str(base_url).rstrip("/"),
        "baud": None,
        "timestamp_unix": timestamp,
        "pose": {
            "x": feedback.get("x"),
            "y": feedback.get("y"),
            "z": feedback.get("z"),
            "tilt": feedback.get("tit"),
        },
        "joints": {
            "base": feedback.get("b"),
            "shoulder": feedback.get("s"),
            "elbow": feedback.get("e"),
            "wrist": feedback.get("t"),
            "roll": feedback.get("r"),
            "gripper": feedback.get("g"),
        },
        "additional_feedback": {
            key: value
            for key, value in feedback.items()
            if key not in {
                "T", "x", "y", "z", "tit", "b", "s", "e", "t", "r", "g"
            }
        },
        "raw_feedback": feedback,
    }


__all__ = [
    "DEFAULT_HTTP_BASE_URL",
    "HTTP_TIMEOUT_S",
    "RoArmHttpClient",
    "RoArmHttpError",
    "RoArmProductionHttpTransport",
    "normalize_feedback",
]
