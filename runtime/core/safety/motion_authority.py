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
    evaluate_motion_permit,
)


def _result(reason, checks):
    return {"allowed": reason == "PERMIT_OK", "reason": reason, "checks": checks}


class MotionNotAuthorized(RuntimeError):
    def __init__(self, reason, checks=None):
        super().__init__(reason)
        self.reason = reason
        self.checks = checks or {}


class LocalMotionAuthority:
    """Issue permits that are valid only within this local authority instance."""

    def __init__(self, *, limits_path=None, audit_path=None, permit_ttl_s=5.0):
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
        safety = evaluate_motion_permit(
            current_state=current_state,
            target=requested,
            guardian_state=guardian_state,
            limits_path=self.limits_path,
            now=current_timestamp,
            max_state_age_s=max_state_age_s,
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
