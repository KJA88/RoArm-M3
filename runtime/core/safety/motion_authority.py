"""Process-local issuance and one-shot consumption of motion permits."""
import math
from threading import Lock
import time
from uuid import uuid4

from .audit import MotionAuditLog
from .motion_permit import (
    DEFAULT_LIMITS_PATH,
    MotionPermit,
    _stamp,
    _timestamp,
    evaluate_gripper_motion_permit,
    evaluate_motion_permit,
)
from .gripper_policy import DEFAULT_GRIPPER_MAP_PATH


def _result(reason, checks):
    return {"allowed": reason == "PERMIT_OK", "reason": reason, "checks": checks}


class MotionNotAuthorized(RuntimeError):
    def __init__(self, reason, checks=None):
        super().__init__(reason)
        self.reason = reason
        self.checks = checks or {}


class LocalMotionAuthority:
    """Issue permits that are valid only within this local authority instance."""

    def __init__(
        self,
        *,
        limits_path=None,
        gripper_map_path=None,
        audit_path=None,
        permit_ttl_s=5.0,
    ):
        if (
            not isinstance(permit_ttl_s, (int, float))
            or isinstance(permit_ttl_s, bool)
            or not math.isfinite(permit_ttl_s)
            or permit_ttl_s <= 0
        ):
            raise ValueError("permit_ttl_s must be a positive finite number")
        self.limits_path = (
            DEFAULT_LIMITS_PATH if limits_path is None else limits_path
        )
        self.gripper_map_path = (
            DEFAULT_GRIPPER_MAP_PATH
            if gripper_map_path is None
            else gripper_map_path
        )
        self.permit_ttl_s = float(permit_ttl_s)
        self.audit = MotionAuditLog(audit_path)
        self._authority_id = str(uuid4())
        self._lock = Lock()

    def issue_permit(
        self,
        *,
        current_state,
        joint,
        target,
        guardian_state=None,
        max_delta=None,
        now=None,
        max_state_age_s=2.0,
    ):
        requested = {"joint": joint, "target": target}
        if max_delta is not None:
            requested["max_delta"] = max_delta
        decision = evaluate_motion_permit(
            current_state=current_state,
            target=requested,
            guardian_state=guardian_state,
            limits_path=self.limits_path,
            now=now,
            max_state_age_s=max_state_age_s,
        )
        if not decision["allowed"]:
            self.audit.record(
                "permit_rejected",
                reason=decision["reason"],
                requested_action="move_joint",
                requested_joint=joint,
                requested_target=target,
            )
            raise MotionNotAuthorized(
                decision["reason"],
                decision["checks"],
            )

        issued_timestamp = _timestamp(time.time() if now is None else now)
        permit = MotionPermit(
            permit_id=str(uuid4()),
            issued_at=_stamp(issued_timestamp),
            expires_at=_stamp(issued_timestamp + self.permit_ttl_s),
            allowed_action="move_joint",
            allowed_joint=joint,
            allowed_target=float(target),
            max_delta=float(max_delta) if max_delta is not None else None,
            consumed=False,
            _authority_id=self._authority_id,
        )
        self.audit.record("permit_issued", **permit.public_dict())
        return permit

    def issue_gripper_permit(
        self,
        *,
        current_state,
        target,
        guardian_state=None,
        now=None,
        max_state_age_s=2.0,
    ):
        decision = evaluate_gripper_motion_permit(
            current_state=current_state,
            target={"joint": "gripper", "target": target},
            guardian_state=guardian_state,
            gripper_map_path=self.gripper_map_path,
            now=now,
            max_state_age_s=max_state_age_s,
        )
        if not decision["allowed"]:
            self.audit.record(
                "permit_rejected",
                reason=decision["reason"],
                requested_action="move_gripper_preset",
                requested_joint="gripper",
                requested_target=target,
            )
            raise MotionNotAuthorized(decision["reason"], decision["checks"])

        issued_timestamp = _timestamp(time.time() if now is None else now)
        permit = MotionPermit(
            permit_id=str(uuid4()),
            issued_at=_stamp(issued_timestamp),
            expires_at=_stamp(issued_timestamp + self.permit_ttl_s),
            allowed_action="move_gripper_preset",
            allowed_joint="gripper",
            allowed_target=float(target),
            max_delta=None,
            consumed=False,
            _authority_id=self._authority_id,
        )
        self.audit.record("permit_issued", **permit.public_dict())
        return permit

    def authorize_once(
        self,
        *,
        permit,
        action,
        joint,
        target,
        current_state,
        guardian_state=None,
        now=None,
        max_state_age_s=2.0,
    ):
        self.audit.record(
            "move_requested",
            permit_id=getattr(permit, "permit_id", None),
            requested_action=action,
            requested_joint=joint,
            requested_target=target,
        )
        with self._lock:
            decision = self._validate_permit(
                permit=permit,
                action=action,
                joint=joint,
                target=target,
                current_state=current_state,
                guardian_state=guardian_state,
                now=now,
                max_state_age_s=max_state_age_s,
            )
            if decision["allowed"]:
                permit.consumed = True

        self.audit.record(
            "permit_accepted" if decision["allowed"] else "permit_rejected",
            permit_id=getattr(permit, "permit_id", None),
            reason=decision["reason"],
            requested_action=action,
            requested_joint=joint,
            requested_target=target,
        )
        return decision

    def authorize_gripper_once(
        self,
        *,
        permit,
        target,
        current_state,
        guardian_state=None,
        now=None,
        max_state_age_s=2.0,
    ):
        action = "move_gripper_preset"
        self.audit.record(
            "move_requested",
            permit_id=getattr(permit, "permit_id", None),
            requested_action=action,
            requested_joint="gripper",
            requested_target=target,
        )
        with self._lock:
            decision = self._validate_permit(
                permit=permit,
                action=action,
                joint="gripper",
                target=target,
                current_state=current_state,
                guardian_state=guardian_state,
                now=now,
                max_state_age_s=max_state_age_s,
                safety_evaluator=evaluate_gripper_motion_permit,
                safety_options={"gripper_map_path": self.gripper_map_path},
            )
            if decision["allowed"]:
                permit.consumed = True
        self.audit.record(
            "permit_accepted" if decision["allowed"] else "permit_rejected",
            permit_id=getattr(permit, "permit_id", None),
            reason=decision["reason"],
            requested_action=action,
            requested_joint="gripper",
            requested_target=target,
        )
        return decision

    def authorize_many_once(
        self,
        *,
        requests,
        current_state,
        guardian_state=None,
        now=None,
        max_state_age_s=2.0,
    ):
        """Atomically consume exact one-shot permits for one combined move."""
        if (
            not isinstance(requests, (list, tuple))
            or not requests
            or any(not isinstance(request, dict) for request in requests)
        ):
            return _result("PERMIT_MISSING", {"requests": []})
        for request in requests:
            self.audit.record(
                "move_requested",
                permit_id=getattr(request.get("permit"), "permit_id", None),
                requested_action=request.get("action"),
                requested_joint=request.get("joint"),
                requested_target=request.get("target"),
            )

        with self._lock:
            decisions = [
                self._validate_permit(
                    permit=request.get("permit"),
                    action=request.get("action"),
                    joint=request.get("joint"),
                    target=request.get("target"),
                    current_state=current_state,
                    guardian_state=guardian_state,
                    now=now,
                    max_state_age_s=max_state_age_s,
                )
                for request in requests
            ]
            rejected = next(
                (decision for decision in decisions if not decision["allowed"]),
                None,
            )
            if rejected is None:
                for request in requests:
                    request["permit"].consumed = True

        for request, decision in zip(requests, decisions):
            self.audit.record(
                "permit_accepted" if decision["allowed"] and rejected is None
                else "permit_rejected",
                permit_id=getattr(request.get("permit"), "permit_id", None),
                reason=decision["reason"] if rejected is None else (
                    rejected["reason"]
                ),
                requested_action=request.get("action"),
                requested_joint=request.get("joint"),
                requested_target=request.get("target"),
            )
        if rejected is not None:
            return _result(
                rejected["reason"],
                {"requests": [decision["checks"] for decision in decisions]},
            )
        return _result(
            "PERMIT_OK",
            {"requests": [decision["checks"] for decision in decisions]},
        )

    def _validate_permit(
        self,
        *,
        permit,
        action,
        joint,
        target,
        current_state,
        guardian_state,
        now,
        max_state_age_s,
        safety_evaluator=evaluate_motion_permit,
        safety_options=None,
    ):
        checks = {
            "permit_present": isinstance(permit, MotionPermit),
            "issuer_matches": False,
            "permit_not_consumed": False,
            "permit_not_expired": False,
            "request_matches": False,
        }
        def done(reason):
            return _result(reason, checks)

        if not checks["permit_present"]:
            return done("PERMIT_MISSING")
        if permit._authority_id != self._authority_id:
            return done("PERMIT_ISSUER_INVALID")
        checks["issuer_matches"] = True
        if permit.consumed:
            return done("PERMIT_CONSUMED")
        checks["permit_not_consumed"] = True

        try:
            current_timestamp = _timestamp(time.time() if now is None else now)
            expires_timestamp = _timestamp(permit.expires_at)
        except (TypeError, ValueError, OverflowError):
            return done("PERMIT_INVALID")
        if current_timestamp >= expires_timestamp:
            return done("PERMIT_EXPIRED")
        checks["permit_not_expired"] = True

        checks["request_matches"] = (
            action == permit.allowed_action
            and joint == permit.allowed_joint
            and isinstance(target, (int, float))
            and not isinstance(target, bool)
            and math.isfinite(target)
            and float(target) == permit.allowed_target
        )
        if not checks["request_matches"]:
            return done("PERMIT_MISMATCH")

        requested = {"joint": joint, "target": target}
        if permit.max_delta is not None:
            requested["max_delta"] = permit.max_delta
        options = (
            {"limits_path": self.limits_path}
            if safety_options is None
            else safety_options
        )
        safety = safety_evaluator(
            current_state=current_state,
            target=requested,
            guardian_state=guardian_state,
            now=current_timestamp,
            max_state_age_s=max_state_age_s,
            **options,
        )
        checks["motion_safety"] = safety["checks"]
        if not safety["allowed"]:
            return done(safety["reason"])
        return done("PERMIT_OK")

    def record_move_start(self, permit):
        self.audit.record("move_start", permit_id=permit.permit_id)

    def record_move_result(self, permit, *, succeeded, error=None):
        self.audit.record(
            "move_success" if succeeded else "move_failure",
            permit_id=permit.permit_id,
            error=None if error is None else str(error),
        )
        self.audit.record("permit_consumed", permit_id=permit.permit_id)

__all__ = ["LocalMotionAuthority", "MotionNotAuthorized"]
