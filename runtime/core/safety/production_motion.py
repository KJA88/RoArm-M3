"""Single production adapter from constrained intent to local execution."""
import json
import math
import os
from pathlib import Path

from .motion_authority import LocalMotionAuthority, MotionNotAuthorized
from .motion_permit import evaluate_motion_permit
from runtime.core.supervisor.mechanical_supervisor import MechanicalSupervisor
from runtime.core.transport.roarm_http import (
    DEFAULT_HTTP_BASE_URL,
    RoArmHttpClient,
    RoArmProductionHttpTransport,
    normalize_feedback,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
GRIPPER_MAP = REPO_ROOT / "runtime/core/calibration/gripper_map.json"
ARM_ONLY_JOINTS = {"base", "shoulder", "elbow", "wrist"}
ALL_STATE_JOINTS = ARM_ONLY_JOINTS | {"roll", "gripper"}


def _denied(action, reason, **details):
    return {
        "ok": False,
        "authorized": False,
        "action": action,
        "reason": reason,
        "hardware_action": "NONE",
        **details,
    }


def _has_finite_joints(current_state, required):
    joints = current_state.get("joints") if isinstance(current_state, dict) else None
    return isinstance(joints, dict) and all(
        isinstance(joints.get(joint), (int, float))
        and not isinstance(joints.get(joint), bool)
        and math.isfinite(joints[joint])
        for joint in required
    )


def _read_state():
    base_url = os.environ.get("ROARM_HTTP_BASE_URL", DEFAULT_HTTP_BASE_URL)
    transport = RoArmHttpClient(base_url)
    try:
        return normalize_feedback(
            transport.read_state(),
            base_url=base_url,
        )
    finally:
        transport.close()


def _open_transport():
    return RoArmProductionHttpTransport(
        os.environ.get("ROARM_HTTP_BASE_URL", DEFAULT_HTTP_BASE_URL)
    )


class ProductionMotionAdapter:
    """Authorize exact intents locally and execute only through the supervisor."""

    def __init__(
        self,
        *,
        state_reader=None,
        transport_factory=None,
        authority=None,
    ):
        self.state_reader = state_reader or _read_state
        self.transport_factory = transport_factory or _open_transport
        self.authority = authority or LocalMotionAuthority()

    def _state(self, action):
        try:
            return self.state_reader(), None
        except Exception as exc:
            return None, _denied(action, "STATE_UNAVAILABLE", error=str(exc))

    def execute_joint(self, joint, target):
        action = "move_joint"
        current_state, denied = self._state(action)
        if denied:
            return denied
        try:
            permit = self.authority.issue_permit(
                current_state=current_state,
                joint=joint,
                target=target,
            )
        except MotionNotAuthorized as exc:
            return _denied(
                action, exc.reason, joint=joint, target=target, checks=exc.checks
            )
        if not _has_finite_joints(current_state, ALL_STATE_JOINTS):
            return _denied(action, "PRESERVATION_STATE_INVALID")

        transport = None
        try:
            transport = self.transport_factory()
            supervisor = MechanicalSupervisor(
                transport=transport,
                authority=self.authority,
            )
            response = supervisor.move_joint(
                joint,
                target,
                permit=permit,
                current_state=current_state,
            )
            return {
                "ok": True,
                "authorized": True,
                "action": action,
                "joint": joint,
                "target": float(target),
                "permit_id": permit.permit_id,
                "permit_consumed": permit.consumed,
                "response": response,
                "hardware_action": "PARTIAL_T102_EXECUTED",
            }
        except Exception as exc:
            return _denied(
                action,
                "EXECUTION_FAILED",
                joint=joint,
                target=target,
                permit_id=permit.permit_id,
                permit_consumed=permit.consumed,
                error=str(exc),
            )
        finally:
            if transport is not None:
                transport.close()

    def execute_arm_pose(self, name, targets):
        if (
            not isinstance(targets, dict)
            or set(targets) != ARM_ONLY_JOINTS
        ):
            return _denied(name, "ARM_POSE_TARGETS_INVALID")
        current_state, denied = self._state(name)
        if denied:
            return denied

        checks = {}
        for joint, target in targets.items():
            decision = evaluate_motion_permit(
                current_state=current_state,
                target={"joint": joint, "target": target},
                limits_path=self.authority.limits_path,
            )
            checks[joint] = decision
            if not decision["allowed"]:
                return _denied(
                    name,
                    decision["reason"],
                    blocked_joint=joint,
                    checks=checks,
                )
        if not _has_finite_joints(current_state, {"roll", "gripper"}):
            return _denied(name, "PRESERVATION_STATE_INVALID")

        permits = {}
        try:
            for joint, target in targets.items():
                permits[joint] = self.authority.issue_permit(
                    current_state=current_state,
                    joint=joint,
                    target=target,
                )
        except MotionNotAuthorized as exc:
            return _denied(name, exc.reason, checks=exc.checks)

        transport = None
        try:
            transport = self.transport_factory()
            supervisor = MechanicalSupervisor(
                transport=transport,
                authority=self.authority,
            )
            response = supervisor.move_arm_pose(
                targets,
                permits=permits,
                current_state=current_state,
            )
            return {
                "ok": True,
                "authorized": True,
                "action": name,
                "targets": {joint: float(value) for joint, value in targets.items()},
                "permit_ids": {
                    joint: permit.permit_id
                    for joint, permit in permits.items()
                },
                "permits_consumed": all(
                    permit.consumed for permit in permits.values()
                ),
                "response": response,
                "hardware_action": "ARM_ONLY_T102_EXECUTED",
            }
        except Exception as exc:
            return _denied(
                name,
                "EXECUTION_FAILED",
                permit_ids={
                    joint: permit.permit_id
                    for joint, permit in permits.items()
                },
                permits_consumed=all(
                    permit.consumed for permit in permits.values()
                ),
                error=str(exc),
            )
        finally:
            if transport is not None:
                transport.close()

    def execute_named_pose(self, name, targets):
        return self.execute_arm_pose(name, targets)

    def execute_named_sequence(self, name, stages):
        """Preflight every target in every stage before allowing movement."""
        current_state, denied = self._state(name)
        if denied:
            return denied
        checks = {}
        normalized_stages = []
        for stage_name, targets in stages:
            normalized = {
                ("gripper" if joint == "hand" else joint): value
                for joint, value in targets.items()
            }
            normalized_stages.append((stage_name, normalized))
            checks[stage_name] = {}
            for joint, target in normalized.items():
                decision = evaluate_motion_permit(
                    current_state=current_state,
                    target={"joint": joint, "target": target},
                    limits_path=self.authority.limits_path,
                )
                checks[stage_name][joint] = decision
                if not decision["allowed"]:
                    return _denied(
                        name,
                        decision["reason"],
                        blocked_stage=stage_name,
                        blocked_joint=joint,
                        checks=checks,
                    )

        results = []
        for stage_name, targets in normalized_stages:
            if len(targets) == 1:
                joint, target = next(iter(targets.items()))
                result = self.execute_joint(joint, target)
            else:
                result = self.execute_arm_pose(stage_name, targets)
            result["stage"] = stage_name
            results.append(result)
            if not result["ok"]:
                return _denied(
                    name, "POSE_EXECUTION_FAILED", results=results
                )
        return {
            "ok": True,
            "authorized": True,
            "action": name,
            "results": results,
            "hardware_action": "NAMED_POSE_EXECUTED",
        }

    def unsupported(self, action, reason="POLICY_NOT_VERIFIED", **details):
        return _denied(action, reason, **details)

    def gripper_finding(self, position):
        try:
            calibration = json.loads(GRIPPER_MAP.read_text(encoding="utf-8"))
            gripper = calibration["gripper"]
            verified = (
                gripper.get("verified_by") == "human"
                and gripper.get("units") == "radians"
            )
        except (OSError, ValueError, KeyError, TypeError):
            gripper, verified = {}, False
        return self.unsupported(
            "set_gripper",
            "GRIPPER_POLICY_REVIEW_REQUIRED",
            requested_position=position,
            calibration_human_verified=verified,
            calibration=gripper if verified else None,
        )


_DEFAULT_ADAPTER = ProductionMotionAdapter()


def execute_joint(joint, target):
    return _DEFAULT_ADAPTER.execute_joint(joint, target)


def execute_named_pose(name, targets):
    return _DEFAULT_ADAPTER.execute_named_pose(name, targets)


def execute_named_sequence(name, stages):
    return _DEFAULT_ADAPTER.execute_named_sequence(name, stages)


def deny_unsupported(action, **details):
    return _DEFAULT_ADAPTER.unsupported(action, **details)


def inspect_gripper(position):
    return _DEFAULT_ADAPTER.gripper_finding(position)


__all__ = [
    "ProductionMotionAdapter",
    "deny_unsupported",
    "execute_joint",
    "execute_named_pose",
    "execute_named_sequence",
    "inspect_gripper",
]
