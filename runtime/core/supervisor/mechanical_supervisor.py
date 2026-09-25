#!/usr/bin/env python3
"""
MechanicalSupervisor with local, one-shot motion authorization.

Construction is inert. No connection, torque, mode, or motion command occurs
until an execution method receives a valid permit from LocalMotionAuthority.
"""
import json

from runtime.core.safety import LocalMotionAuthority, MotionNotAuthorized


class MechanicalSupervisor:
    def __init__(self, *, transport=None, authority=None):
        self._transport = transport
        self.authority = authority or LocalMotionAuthority()

    def move_joint(
        self,
        joint,
        target,
        *,
        permit,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Execute one fixed-protocol joint move after local authorization."""
        decision = self.authority.authorize_once(
            permit=permit,
            action="move_joint",
            joint=joint,
            target=target,
            current_state=current_state,
            guardian_state=guardian_state,
            now=now,
        )
        if not decision["allowed"]:
            raise MotionNotAuthorized(decision["reason"], decision["checks"])

        if self._transport is None:
            error = RuntimeError("No local motion transport is configured")
            self.authority.record_move_result(
                permit,
                succeeded=False,
                error=error,
            )
            raise error

        self.authority.record_move_start(permit)
        try:
            payload = json.dumps(
                {
                    "T": 102,
                    joint: float(target),
                    "spd": 0,
                    "acc": 0,
                },
                separators=(",", ":"),
            ) + "\n"
            self._transport.write(payload.encode("ascii"))
            response = self._transport.readline()
        except Exception as exc:
            self.authority.record_move_result(
                permit,
                succeeded=False,
                error=exc,
            )
            raise
        self.authority.record_move_result(permit, succeeded=True)
        return response.decode("ascii", errors="ignore").strip()

    def move_to_pose(
        self,
        x,
        y,
        z,
        pitch,
        *,
        permit,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Keep task-space motion behind the gate pending verified pose policy."""
        decision = self.authority.authorize_once(
            permit=permit,
            action="move_to_pose",
            joint="task_pose",
            target=pitch,
            current_state=current_state,
            guardian_state=guardian_state,
            now=now,
        )
        raise MotionNotAuthorized(decision["reason"], decision["checks"])

    def close(self):
        if self._transport is not None:
            self._transport.close()