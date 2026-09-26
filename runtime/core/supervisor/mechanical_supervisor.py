#!/usr/bin/env python3
"""
MechanicalSupervisor with local, one-shot motion authorization.

Construction is inert. No connection, torque, mode, or motion command occurs
until an execution method receives a valid permit from LocalMotionAuthority.
"""
import math

from runtime.core.safety import LocalMotionAuthority, MotionNotAuthorized


ARM_JOINTS = {"base", "shoulder", "elbow", "wrist"}
ALL_STATE_JOINTS = ARM_JOINTS | {"roll", "gripper"}


def _finite_joint_state(current_state, required):
    joints = current_state.get("joints") if isinstance(current_state, dict) else None
    if not isinstance(joints, dict):
        raise MotionNotAuthorized("PRESERVATION_STATE_INVALID")
    values = {joint: joints.get(joint) for joint in required}
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        for value in values.values()
    ):
        raise MotionNotAuthorized("PRESERVATION_STATE_INVALID")
    return values


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
        current_joints = _finite_joint_state(
            current_state,
            ALL_STATE_JOINTS,
        )
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
            response = self._transport.move_joint(
                joint,
                float(target),
                current_joints=current_joints,
            )
        except Exception as exc:
            self.authority.record_move_result(
                permit,
                succeeded=False,
                error=exc,
            )
            raise
        self.authority.record_move_result(permit, succeeded=True)
        return response

    def move_arm_pose(
        self,
        targets,
        *,
        permits,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Execute one combined arm-only command after atomic authorization."""
        if (
            not isinstance(targets, dict)
            or set(targets) != ARM_JOINTS
            or not isinstance(permits, dict)
        ):
            raise MotionNotAuthorized("PERMIT_MISSING")
        preserved = _finite_joint_state(
            current_state,
            {"roll", "gripper"},
        )
        requests = [
            {
                "permit": permits.get(joint),
                "action": "move_joint",
                "joint": joint,
                "target": target,
            }
            for joint, target in targets.items()
        ]
        decision = self.authority.authorize_many_once(
            requests=requests,
            current_state=current_state,
            guardian_state=guardian_state,
            now=now,
        )
        if not decision["allowed"]:
            raise MotionNotAuthorized(decision["reason"], decision["checks"])

        consumed_permits = [request["permit"] for request in requests]
        if self._transport is None:
            error = RuntimeError("No local motion transport is configured")
            for permit in consumed_permits:
                self.authority.record_move_result(
                    permit,
                    succeeded=False,
                    error=error,
                )
            raise error

        for permit in consumed_permits:
            self.authority.record_move_start(permit)
        try:
            response = self._transport.move_arm_pose(
                targets,
                roll=preserved["roll"],
                hand=preserved["gripper"],
            )
        except Exception as exc:
            for permit in consumed_permits:
                self.authority.record_move_result(
                    permit,
                    succeeded=False,
                    error=exc,
                )
            raise
        for permit in consumed_permits:
            self.authority.record_move_result(permit, succeeded=True)
        return response

    def move_gripper_preset(
        self,
        target,
        *,
        permit,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Command one verified gripper preset while preserving every other joint."""
        current_joints = _finite_joint_state(current_state, ALL_STATE_JOINTS)
        decision = self.authority.authorize_gripper_once(
            permit=permit,
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
                permit, succeeded=False, error=error
            )
            raise error

        self.authority.record_move_start(permit)
        try:
            response = self._transport.move_gripper_preset(
                float(target),
                current_joints=current_joints,
            )
        except Exception as exc:
            self.authority.record_move_result(
                permit, succeeded=False, error=exc
            )
            raise
        self.authority.record_move_result(permit, succeeded=True)
        return response

    def move_base_scan(
        self,
        target,
        *,
        permit,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Execute one fixed-purpose demonstrated base scan endpoint."""
        decision = self.authority.authorize_once(
            permit=permit,
            action="move_joint",
            joint="base",
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
            response = self._transport.move_base_scan(float(target))
        except Exception as exc:
            self.authority.record_move_result(
                permit,
                succeeded=False,
                error=exc,
            )
            raise
        self.authority.record_move_result(permit, succeeded=True)
        return response

    def move_named_task_probe(
        self,
        target,
        *,
        permit,
        current_state,
        guardian_state=None,
        now=None,
    ):
        """Execute the fixed center T:104 probe after one-shot authorization."""
        raw = (
            current_state.get("raw_feedback")
            if isinstance(current_state, dict)
            else None
        )
        preserved = {
            "roll": raw.get("r") if isinstance(raw, dict) else None,
            "gripper": raw.get("g") if isinstance(raw, dict) else None,
        }
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in preserved.values()
        ):
            raise MotionNotAuthorized("TASK_STATE_INVALID")
        decision = self.authority.authorize_task_space_once(
            permit=permit,
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
                permit, succeeded=False, error=error
            )
            raise error

        self.authority.record_move_start(permit)
        try:
            response = self._transport.move_named_task_probe(
                target["name"],
                roll=preserved["roll"],
                gripper=preserved["gripper"],
            )
        except Exception as exc:
            self.authority.record_move_result(
                permit, succeeded=False, error=exc
            )
            raise
        self.authority.record_move_result(permit, succeeded=True)
        return response

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