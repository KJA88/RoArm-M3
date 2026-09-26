"""Single production adapter from constrained intent to local execution."""
import json
import math
import os
from pathlib import Path
import time

from .existing_motions import (
    SCAN_LEFT_BASE_TARGET,
    SCAN_RIGHT_BASE_TARGET,
)
from .gripper_policy import resolve_gripper_preset
from .task_space_policy import NAMED_TASK_PROBES
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
SCAN_ENDPOINTS = {
    "scan_left_arm_only": SCAN_LEFT_BASE_TARGET["base"],
    "scan_right_arm_only": SCAN_RIGHT_BASE_TARGET["base"],
}


def _denied(action, reason, **details):
    return {
        "ok": False,
        "authorized": False,
        "action": action,
        "reason": reason,
        "hardware_action": "NONE",
        **details,
    }


def _uncertain(
    action,
    *,
    hardware_action="T102_OUTCOME_UNCERTAIN",
    **details,
):
    return {
        "ok": False,
        "authorized": True,
        "action": action,
        "reason": "EXECUTION_OUTCOME_UNCERTAIN",
        "hardware_action": hardware_action,
        "position_verified": False,
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
        sleep_fn=time.sleep,
    ):
        self.state_reader = state_reader or _read_state
        self.transport_factory = transport_factory or _open_transport
        self.authority = authority or LocalMotionAuthority()
        self.sleep_fn = sleep_fn

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
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
            }
        except Exception as exc:
            if permit.consumed:
                return _uncertain(
                    action,
                    joint=joint,
                    target=target,
                    permit_id=permit.permit_id,
                    permit_consumed=True,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
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
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
            }
        except Exception as exc:
            permits_consumed = all(
                permit.consumed for permit in permits.values()
            )
            if permits_consumed:
                return _uncertain(
                    name,
                    permit_ids={
                        joint: permit.permit_id
                        for joint, permit in permits.items()
                    },
                    permits_consumed=True,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            return _denied(
                name,
                "EXECUTION_FAILED",
                permit_ids={
                    joint: permit.permit_id
                    for joint, permit in permits.items()
                },
                permits_consumed=False,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        finally:
            if transport is not None:
                transport.close()

    def execute_named_pose(self, name, targets):
        return self.execute_arm_pose(name, targets)

    def execute_gripper_preset(self, preset):
        action = "set_gripper"
        try:
            target = resolve_gripper_preset(
                preset, self.authority.gripper_map_path
            )
        except ValueError as exc:
            return _denied(action, str(exc), requested_preset=preset)
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return _denied(
                action,
                "GRIPPER_MAP_UNREADABLE",
                requested_preset=preset,
            )

        current_state, denied = self._state(action)
        if denied:
            return denied
        if not _has_finite_joints(current_state, ALL_STATE_JOINTS):
            return _denied(action, "PRESERVATION_STATE_INVALID")
        try:
            permit = self.authority.issue_gripper_permit(
                current_state=current_state,
                target=target,
            )
        except MotionNotAuthorized as exc:
            return _denied(
                action,
                exc.reason,
                requested_preset=preset,
                target=target,
                checks=exc.checks,
            )

        transport = None
        try:
            transport = self.transport_factory()
            supervisor = MechanicalSupervisor(
                transport=transport,
                authority=self.authority,
            )
            response = supervisor.move_gripper_preset(
                target,
                permit=permit,
                current_state=current_state,
            )
            return {
                "ok": True,
                "authorized": True,
                "action": action,
                "preset": preset,
                "target": target,
                "permit_id": permit.permit_id,
                "permit_consumed": permit.consumed,
                "response": response,
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
            }
        except Exception as exc:
            if permit.consumed:
                return _uncertain(
                    action,
                    preset=preset,
                    target=target,
                    permit_id=permit.permit_id,
                    permit_consumed=True,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            return _denied(
                action,
                "EXECUTION_FAILED",
                requested_preset=preset,
                target=target,
                permit_id=permit.permit_id,
                permit_consumed=False,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        finally:
            if transport is not None:
                transport.close()

    def execute_named_task_probe(self, name):
        action = name if isinstance(name, str) else "task_probe"
        target = NAMED_TASK_PROBES.get(name)
        if target is None:
            return _denied(
                action,
                "TASK_PROBE_NOT_AUTHORIZED",
                requested_probe=name,
            )
        target = dict(target)
        current_state, denied = self._state(action)
        if denied:
            return denied
        try:
            permit = self.authority.issue_task_space_permit(
                current_state=current_state,
                target=target,
            )
        except MotionNotAuthorized as exc:
            return _denied(action, exc.reason, target=target, checks=exc.checks)

        transport = None
        try:
            transport = self.transport_factory()
            supervisor = MechanicalSupervisor(
                transport=transport,
                authority=self.authority,
            )
            response = supervisor.move_named_task_probe(
                target,
                permit=permit,
                current_state=current_state,
            )
            return {
                "ok": True,
                "authorized": True,
                "action": action,
                "target": target,
                "permit_id": permit.permit_id,
                "permit_consumed": permit.consumed,
                "response": response,
                "hardware_action": "T104_RESPONSE_RECEIVED",
                "position_verified": False,
            }
        except Exception as exc:
            if permit.consumed:
                return _uncertain(
                    action,
                    hardware_action="T104_OUTCOME_UNCERTAIN",
                    target=target,
                    permit_id=permit.permit_id,
                    permit_consumed=True,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            return _denied(
                action,
                "EXECUTION_FAILED",
                target=target,
                permit_id=permit.permit_id,
                permit_consumed=False,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        finally:
            if transport is not None:
                transport.close()

    def execute_scan(self, name, ready_targets, endpoint):
        expected_endpoint = SCAN_ENDPOINTS.get(name)
        if (
            expected_endpoint is None
            or not isinstance(endpoint, (int, float))
            or isinstance(endpoint, bool)
            or float(endpoint) != expected_endpoint
        ):
            return _denied(name, "SCAN_ENDPOINT_NOT_AUTHORIZED")

        ready = self.execute_arm_pose("ready_arm_only", ready_targets)
        ready["stage"] = "ready_arm_only"
        if not ready["ok"]:
            if ready.get("reason") == "EXECUTION_OUTCOME_UNCERTAIN":
                return _uncertain(
                    name,
                    results=[ready],
                    uncertain_stage="ready_arm_only",
                    error=ready.get("error"),
                    error_type=ready.get("error_type"),
                )
            return _denied(name, "READY_STAGE_FAILED", results=[ready])

        try:
            self.sleep_fn(3.0)
        except Exception as exc:
            return {
                "ok": False,
                "authorized": True,
                "action": name,
                "reason": "SCAN_DWELL_FAILED",
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "results": [ready],
            }

        current_state, denied = self._state(name)
        if denied:
            return {
                "ok": False,
                "authorized": True,
                "action": name,
                "reason": "SCAN_STATE_UNAVAILABLE",
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
                "state_error": denied,
                "results": [ready],
            }
        try:
            permit = self.authority.issue_permit(
                current_state=current_state,
                joint="base",
                target=endpoint,
            )
        except MotionNotAuthorized as exc:
            return {
                "ok": False,
                "authorized": True,
                "action": name,
                "reason": exc.reason,
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
                "checks": exc.checks,
                "results": [ready],
            }

        transport = None
        try:
            transport = self.transport_factory()
            supervisor = MechanicalSupervisor(
                transport=transport,
                authority=self.authority,
            )
            response = supervisor.move_base_scan(
                endpoint,
                permit=permit,
                current_state=current_state,
            )
            scan = {
                "ok": True,
                "authorized": True,
                "action": "base_scan",
                "stage": "base_scan",
                "target": float(endpoint),
                "permit_id": permit.permit_id,
                "permit_consumed": permit.consumed,
                "response": response,
                "hardware_action": "T101_RESPONSE_RECEIVED",
                "position_verified": False,
            }
            return {
                "ok": True,
                "authorized": True,
                "action": name,
                "results": [ready, scan],
                "hardware_action": "SCAN_COMMAND_RESPONSES_RECEIVED",
                "position_verified": False,
            }
        except Exception as exc:
            if permit.consumed:
                scan = _uncertain(
                    "base_scan",
                    hardware_action="T101_OUTCOME_UNCERTAIN",
                    target=float(endpoint),
                    permit_id=permit.permit_id,
                    permit_consumed=True,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                scan["stage"] = "base_scan"
                return _uncertain(
                    name,
                    hardware_action="T101_OUTCOME_UNCERTAIN",
                    uncertain_stage="base_scan",
                    results=[ready, scan],
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            return {
                "ok": False,
                "authorized": True,
                "action": name,
                "reason": "SCAN_EXECUTION_NOT_STARTED",
                "hardware_action": "T102_RESPONSE_RECEIVED",
                "position_verified": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "results": [ready],
            }
        finally:
            if transport is not None:
                transport.close()

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
                if result.get("reason") == "EXECUTION_OUTCOME_UNCERTAIN":
                    return _uncertain(
                        name,
                        uncertain_stage=stage_name,
                        results=results,
                        error=result.get("error"),
                        error_type=result.get("error_type"),
                    )
                if any(completed.get("ok") for completed in results[:-1]):
                    return {
                        "ok": False,
                        "authorized": True,
                        "action": name,
                        "reason": "POSE_EXECUTION_INCOMPLETE",
                        "hardware_action": (
                            "T102_SEQUENCE_PARTIAL_RESPONSES_RECEIVED"
                        ),
                        "position_verified": False,
                        "failed_stage": stage_name,
                        "results": results,
                    }
                return _denied(
                    name, "POSE_EXECUTION_FAILED", results=results
                )
        return {
            "ok": True,
            "authorized": True,
            "action": name,
            "results": results,
            "hardware_action": "T102_SEQUENCE_RESPONSES_RECEIVED",
            "position_verified": False,
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


def execute_scan(name, ready_targets, endpoint):
    return _DEFAULT_ADAPTER.execute_scan(name, ready_targets, endpoint)


def execute_gripper_position(preset):
    return _DEFAULT_ADAPTER.execute_gripper_preset(preset)


def execute_named_task_probe(name):
    return _DEFAULT_ADAPTER.execute_named_task_probe(name)


def execute_task_probe_center():
    return execute_named_task_probe("task_probe_center")


def deny_unsupported(action, **details):
    return _DEFAULT_ADAPTER.unsupported(action, **details)


def inspect_gripper(position):
    return _DEFAULT_ADAPTER.gripper_finding(position)


__all__ = [
    "ProductionMotionAdapter",
    "deny_unsupported",
    "execute_joint",
    "execute_gripper_position",
    "execute_named_pose",
    "execute_named_sequence",
    "execute_named_task_probe",
    "execute_scan",
    "execute_task_probe_center",
    "inspect_gripper",
]
