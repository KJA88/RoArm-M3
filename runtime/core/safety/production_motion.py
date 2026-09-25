"""Single production adapter from constrained intent to local execution."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path

from .motion_authority import LocalMotionAuthority, MotionNotAuthorized
from .motion_permit import evaluate_motion_permit
from runtime.core.supervisor.mechanical_supervisor import MechanicalSupervisor


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_READER = (
    REPO_ROOT
    / "milestones/Phase_1_System_Authority/03_deterministic_pipelines"
    / "milestone_03_state_reader.py"
)
GRIPPER_MAP = REPO_ROOT / "runtime/core/calibration/gripper_map.json"


def _denied(action, reason, **details):
    return {
        "ok": False,
        "authorized": False,
        "action": action,
        "reason": reason,
        "hardware_action": "NONE",
        **details,
    }


@lru_cache(maxsize=1)
def _state_module():
    spec = importlib.util.spec_from_file_location(
        "roarm_production_state_reader", STATE_READER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("RoArm state reader is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_state():
    return _state_module().get_feedback()


def _open_transport():
    import serial

    module = _state_module()
    transport = serial.Serial(
        module.choose_port(),
        module.BAUD,
        timeout=1.0,
        dsrdtr=None,
    )
    transport.setRTS(False)
    transport.setDTR(False)
    return transport


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

    def execute_named_pose(self, name, targets):
        return self.execute_named_sequence(name, (("pose", targets),))

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
            for joint, target in targets.items():
                result = self.execute_joint(joint, target)
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
