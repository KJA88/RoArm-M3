#!/usr/bin/env python3
"""Operator-driven base and gripper verification; never updates calibration."""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import requests
import time
from uuid import uuid4


HTTP_TIMEOUT = 5.0
DEFAULT_HTTP_BASE_URL = "http://192.168.4.1"
LOG_DIR = (
    Path(__file__).resolve().parents[3]
    / "runtime/core/calibration/logs"
)
BASE_STEPS = {0.01, 0.05}
TORQUE_ON = "ON"
TORQUE_OFF = "OFF"
TORQUE_UNKNOWN = "UNKNOWN"
GRIPPER_PRESETS = {
    "open": 1.6,
    "light": 2.0,
    "firm": 2.4,
    "pinch": 2.8,
}


class VerificationError(RuntimeError):
    """Fail-closed verification error."""


class RoArmHttpTransport:
    """Fixed-purpose HTTP transport; no arbitrary command surface."""

    def __init__(
        self,
        base_url=DEFAULT_HTTP_BASE_URL,
        *,
        timeout_s=HTTP_TIMEOUT,
        session=None,
    ):
        self.base_url = str(base_url).rstrip("/")
        if not self.base_url:
            raise ValueError("ROARM_HTTP_BASE_URL must not be empty")
        self.timeout_s = float(timeout_s)
        self._session = requests.Session() if session is None else session
        self._session.trust_env = False

    def _get(self, packet):
        command = json.dumps(packet, separators=(",", ":"))
        url = f"{self.base_url}/js?json={command}"
        response = self._session.get(url, timeout=self.timeout_s)
        response.raise_for_status()
        result = json.loads(response.text)
        if not isinstance(result, dict):
            raise VerificationError("HTTP_RESPONSE_NOT_OBJECT")
        return result

    def read_state(self):
        return self._get({"T": 105})

    def set_torque(self, enabled):
        return self._get({"T": 210, "cmd": 1 if enabled else 0})

    def move_base(self, target):
        return self._get(
            {
                "T": 101,
                "joint": 1,
                "rad": float(target),
                "spd": 50,
                "acc": 0,
            }
        )

    def move_gripper(self, target):
        return self._get(
            {
                "T": 101,
                "joint": 6,
                "rad": float(target),
                "spd": 50,
                "acc": 0,
            }
        )


def _utc_now():
    return datetime.now(timezone.utc)


def _stamp(value=None):
    value = _utc_now() if value is None else value
    return value.isoformat().replace("+00:00", "Z")


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


class CalibrationLog:
    """Append-only JSONL log with collision-safe session filenames."""

    def __init__(self, directory=LOG_DIR, now=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        now = _utc_now() if now is None else now
        prefix = now.strftime("%Y%m%dT%H%M%S.%fZ")
        while True:
            path = self.directory / (
                f"base_gripper_verification_{prefix}_{uuid4().hex[:8]}.jsonl"
            )
            try:
                path.touch(exist_ok=False)
            except FileExistsError:
                continue
            self.path = path
            break

    def record(self, event, **details):
        entry = {"timestamp": _stamp(), "event": event, **details}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(entry, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
        return entry


class BaseGripperVerification:
    """Fixed-command calibration session with injectable transport."""

    def __init__(
        self,
        transport,
        log,
        *,
        settle_s=0.5,
        sleep_fn=time.sleep,
    ):
        self.transport = transport
        self.log = log
        self.settle_s = float(settle_s)
        if not math.isfinite(self.settle_s) or self.settle_s < 0:
            raise ValueError("settle time must be finite and non-negative")
        self.sleep_fn = sleep_fn
        self.started = False
        self.torque_state = TORQUE_UNKNOWN
        self.motion_blocked = False
        self.state_unknown = False
        self.current_state = None
        self.pending_confirmation = None
        self.last_base_confirmation = None
        self.base_candidates = {
            "negative_limit": None,
            "positive_limit": None,
        }
        self.gripper_results = {}
        self._closed = False

    def _fixed_request(self, packet, purpose, request):
        self.log.record("command", purpose=purpose, packet=packet)
        response = request()
        self.log.record(
            "command_response", purpose=purpose, response=response
        )
        return response

    def _request_state(self, purpose):
        try:
            packet = self._fixed_request(
                {"T": 105},
                purpose,
                self.transport.read_state,
            )
        except Exception as exc:
            self.log.record(
                "readback_failed", purpose=purpose, error=str(exc)
            )
            raise VerificationError("T105_READBACK_FAILED") from exc
        if packet.get("T") != 1051:
            self.log.record(
                "readback_failed",
                purpose=purpose,
                error="HTTP feedback did not contain T=1051",
                packet=packet,
            )
            raise VerificationError("T105_READBACK_INVALID")
        if not _finite(packet.get("b")) or not _finite(packet.get("g")):
            self.log.record(
                "readback_failed",
                purpose=purpose,
                error="T1051 missing finite b/g",
                packet=packet,
            )
            raise VerificationError("T105_READBACK_INVALID")

        state = {
            "base": float(packet["b"]),
            "gripper": float(packet["g"]),
            "raw": packet,
        }
        self.log.record("readback", purpose=purpose, state=state)
        return state

    def startup(self):
        if self.started:
            raise VerificationError("SESSION_ALREADY_STARTED")
        state = self._request_state("startup_state")
        self.current_state = state
        self.started = True
        self.state_unknown = False
        self.log.record("initial_state", state=state)
        return state

    def enable_torque(self):
        self._require_started()
        if self.motion_blocked:
            raise VerificationError("MOTION_BLOCKED_RECOVERY_REQUIRED")
        try:
            self._fixed_request(
                {"T": 210, "cmd": 1},
                "enable_torque",
                lambda: self.transport.set_torque(True),
            )
        except Exception as exc:
            self.torque_state = TORQUE_UNKNOWN
            self.log.record(
                "torque_command_failed",
                requested_state=TORQUE_ON,
                torque_state=TORQUE_UNKNOWN,
                error=str(exc),
            )
            raise VerificationError("TORQUE_ENABLE_FAILED_STATE_UNKNOWN") from exc
        self.torque_state = TORQUE_ON
        self.log.record("torque_enabled", torque_state=TORQUE_ON)

    def disable_torque(self):
        try:
            self._fixed_request(
                {"T": 210, "cmd": 0},
                "disable_torque",
                lambda: self.transport.set_torque(False),
            )
        except Exception as exc:
            self.torque_state = TORQUE_UNKNOWN
            self.log.record(
                "torque_command_failed",
                requested_state=TORQUE_OFF,
                torque_state=TORQUE_UNKNOWN,
                error=str(exc),
            )
            raise VerificationError("TORQUE_DISABLE_FAILED_STATE_UNKNOWN") from exc
        self.torque_state = TORQUE_OFF
        self.log.record("torque_disabled", torque_state=TORQUE_OFF)

    def recover_readback(self):
        if not self.started:
            raise VerificationError("VALID_STARTUP_STATE_REQUIRED")
        state = self._request_state("explicit_readback_recovery")
        self.current_state = state
        self.motion_blocked = False
        self.state_unknown = False
        self.log.record("motion_recovered", state=state)
        return state

    def jog_base(self, delta):
        self._require_motion_ready()
        if not _finite(delta) or abs(float(delta)) not in BASE_STEPS:
            raise VerificationError("BASE_JOG_MUST_BE_0.01_OR_0.05")
        target = self.current_state["base"] + float(delta)
        return self._move_isolated(
            joint_id=1,
            state_field="base",
            target=target,
            purpose="base_jog",
        )

    def move_gripper(self, target):
        self._require_motion_ready()
        if not _finite(target) or float(target) not in GRIPPER_PRESETS.values():
            raise VerificationError("GRIPPER_TARGET_NOT_VERIFIED_PRESET")
        return self._move_isolated(
            joint_id=6,
            state_field="gripper",
            target=float(target),
            purpose="gripper_preset",
        )

    def _move_isolated(self, *, joint_id, state_field, target, purpose):
        packet = {
            "T": 101,
            "joint": joint_id,
            "rad": float(target),
            "spd": 50,
            "acc": 0,
        }
        if joint_id == 1:
            request = lambda: self.transport.move_base(target)
        elif joint_id == 6:
            request = lambda: self.transport.move_gripper(target)
        else:
            raise VerificationError("JOINT_NOT_ALLOWED")
        try:
            self._fixed_request(packet, purpose, request)
        except Exception as exc:
            self._block_motion_unknown(
                reason="MOTION_COMMAND_FAILED",
                purpose=purpose,
                commanded_target=target,
                error=str(exc),
            )
            raise VerificationError("MOTION_COMMAND_FAILED_STATE_UNKNOWN") from exc
        self.sleep_fn(self.settle_s)
        try:
            state = self._request_state(f"{purpose}_readback")
        except VerificationError:
            self._block_motion_unknown(
                reason="POST_MOTION_READBACK_FAILED",
                purpose=purpose,
                commanded_target=target,
            )
            raise

        self.current_state = state
        reported = state[state_field]
        result = {
            "mode": state_field,
            "commanded": float(target),
            "reported": reported,
            "error": reported - float(target),
        }
        self.pending_confirmation = result
        self.log.record("motion_result", **result)
        return result

    def _block_motion_unknown(self, **details):
        self.motion_blocked = True
        self.state_unknown = True
        self.current_state = None
        self.log.record(
            "motion_blocked",
            state="UNKNOWN",
            torque_state=self.torque_state,
            **details,
        )

    def confirm_base(self, acceptable, note=""):
        pending = self._require_pending("base")
        confirmation = {
            **pending,
            "acceptable": bool(acceptable),
            "note": str(note),
        }
        self.last_base_confirmation = confirmation
        self.pending_confirmation = None
        self.log.record("operator_confirmation", **confirmation)
        return confirmation

    def record_base_candidate(self, which, note=""):
        if which not in self.base_candidates:
            raise VerificationError("BASE_CANDIDATE_MUST_BE_NEGATIVE_OR_POSITIVE")
        confirmation = self.last_base_confirmation
        if not confirmation or confirmation["acceptable"] is not True:
            raise VerificationError("BASE_POSITION_NOT_CONFIRMED_ACCEPTABLE")
        candidate = {
            "value": confirmation["reported"],
            "commanded": confirmation["commanded"],
            "note": str(note),
        }
        self.base_candidates[which] = candidate
        self.log.record(
            "base_limit_candidate", candidate_type=which, **candidate
        )
        return candidate

    def confirm_gripper(
        self,
        *,
        direction_ok,
        physical_opening,
        buzzing_or_stall,
        excessive_force,
        acceptable,
        note="",
    ):
        pending = self._require_pending("gripper")
        passed = (
            bool(direction_ok)
            and not bool(buzzing_or_stall)
            and not bool(excessive_force)
            and bool(acceptable)
        )
        name = next(
            key
            for key, value in GRIPPER_PRESETS.items()
            if value == pending["commanded"]
        )
        confirmation = {
            **pending,
            "preset": name,
            "status": "PASS" if passed else "FAIL",
            "direction_ok": bool(direction_ok),
            "physical_opening": str(physical_opening),
            "buzzing_or_stall": bool(buzzing_or_stall),
            "excessive_force": bool(excessive_force),
            "acceptable": bool(acceptable),
            "note": str(note),
        }
        self.gripper_results[name] = confirmation
        self.pending_confirmation = None
        self.log.record("operator_confirmation", **confirmation)
        return confirmation

    def proposed_base_json(self):
        def value(name):
            candidate = self.base_candidates[name]
            return None if candidate is None else candidate["value"]

        notes = [
            candidate["note"]
            for candidate in self.base_candidates.values()
            if candidate and candidate["note"]
        ]
        return {
            "1": {
                "name": "Base",
                "negative_limit": value("negative_limit"),
                "positive_limit": value("positive_limit"),
                "units": "radians",
                "verified_by": "human",
                "milestone": "02_mechanical_truth",
                "note": " | ".join(notes),
            }
        }

    def summary(self):
        return {
            "base_candidates": self.base_candidates,
            "proposed_base_json": self.proposed_base_json(),
            "gripper_results": self.gripper_results,
            "motion_blocked": self.motion_blocked,
            "state_unknown": self.state_unknown,
            "torque_state": self.torque_state,
        }

    def shutdown(self):
        if self._closed:
            return
        try:
            self.log.record("final_summary", summary=self.summary())
        finally:
            close = getattr(self.transport, "close", None)
            if close is not None:
                close()
            self._closed = True

    def _require_started(self):
        if not self.started or self.current_state is None:
            raise VerificationError("VALID_STARTUP_STATE_REQUIRED")

    def _require_motion_ready(self):
        if self.motion_blocked:
            raise VerificationError("MOTION_BLOCKED_RECOVERY_REQUIRED")
        self._require_started()
        if self.torque_state == TORQUE_UNKNOWN:
            raise VerificationError("TORQUE_STATE_UNKNOWN")
        if self.torque_state != TORQUE_ON:
            raise VerificationError("TORQUE_NOT_ENABLED")
        if self.pending_confirmation is not None:
            raise VerificationError("OPERATOR_CONFIRMATION_REQUIRED")

    def _require_pending(self, mode):
        pending = self.pending_confirmation
        if not pending or pending["mode"] != mode:
            raise VerificationError(f"NO_PENDING_{mode.upper()}_CONFIRMATION")
        return pending


def _yes(prompt, input_fn):
    return input_fn(prompt).strip().lower() in {"y", "yes"}


def _confirm_base(session, input_fn, output):
    acceptable = _yes("Physically acceptable? [y/N]: ", input_fn)
    note = input_fn("Observation note: ").strip()
    result = session.confirm_base(acceptable, note)
    output(json.dumps(result, indent=2))


def _base_mode(session, input_fn, output):
    output(
        "Base: +=+0.05, -=-0.05, f+=+0.01, f-=-0.01, "
        "negative/positive=record candidate, back"
    )
    while True:
        command = input_fn("base> ").strip().lower()
        if command == "back":
            return
        if command in {"+", "-", "f+", "f-"}:
            delta = {"+": 0.05, "-": -0.05, "f+": 0.01, "f-": -0.01}[
                command
            ]
            output(json.dumps(session.jog_base(delta), indent=2))
            _confirm_base(session, input_fn, output)
        elif command in {"negative", "positive"}:
            note = input_fn("Candidate note: ").strip()
            key = f"{command}_limit"
            output(
                json.dumps(
                    session.record_base_candidate(key, note), indent=2
                )
            )
        else:
            output("Unknown base command.")


def _gripper_mode(session, input_fn, output):
    output("Gripper targets: 1.6, 2.0, 2.4, 2.8; or back")
    while True:
        raw = input_fn("gripper> ").strip().lower()
        if raw == "back":
            return
        try:
            target = float(raw)
        except ValueError:
            output("Enter one listed target or back.")
            continue
        output(json.dumps(session.move_gripper(target), indent=2))
        confirmation = session.confirm_gripper(
            direction_ok=_yes("Direction correct? [y/N]: ", input_fn),
            physical_opening=input_fn("Describe physical opening: ").strip(),
            buzzing_or_stall=_yes("Any buzzing/stall? [y/N]: ", input_fn),
            excessive_force=_yes("Any excessive force? [y/N]: ", input_fn),
            acceptable=_yes("Accept target? [y/N]: ", input_fn),
            note=input_fn("Observation note: ").strip(),
        )
        output(json.dumps(confirmation, indent=2))


def run_interactive(session, input_fn=input, output=print):
    try:
        state = session.startup()
        output(
            f"Read-only startup OK: base b={state['base']:.6f}, "
            f"gripper g={state['gripper']:.6f}"
        )
        output(
            "Commands: enable, disable, base, gripper, state, recover, "
            "summary, quit"
        )
        while True:
            try:
                command = input_fn("verify> ").strip().lower()
                if command == "quit":
                    break
                if command == "enable":
                    session.enable_torque()
                    output("Torque enabled explicitly.")
                elif command == "disable":
                    session.disable_torque()
                    output("Torque disabled.")
                elif command == "base":
                    _base_mode(session, input_fn, output)
                elif command == "gripper":
                    _gripper_mode(session, input_fn, output)
                elif command == "state":
                    output(json.dumps(session.current_state, indent=2))
                elif command == "recover":
                    output(
                        json.dumps(session.recover_readback(), indent=2)
                    )
                elif command == "summary":
                    output(json.dumps(session.summary(), indent=2))
                else:
                    output("Unknown command.")
            except VerificationError as exc:
                output(f"DENIED: {exc}")
    except KeyboardInterrupt:
        output("\nCtrl+C received; exiting without changing torque state.")
    finally:
        session.shutdown()
        output("Final verification summary:")
        output(json.dumps(session.summary(), indent=2))
        output(f"Log: {session.log.path}")


def _open_http():
    base_url = os.environ.get(
        "ROARM_HTTP_BASE_URL",
        DEFAULT_HTTP_BASE_URL,
    )
    return RoArmHttpTransport(base_url)


def main():
    log = CalibrationLog()
    transport = _open_http()
    session = BaseGripperVerification(transport, log)
    run_interactive(session)


if __name__ == "__main__":
    main()
