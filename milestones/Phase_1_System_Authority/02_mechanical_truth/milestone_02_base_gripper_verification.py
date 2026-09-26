#!/usr/bin/env python3
"""Operator-driven base and gripper verification; never updates calibration."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from uuid import uuid4


BAUD = 115200
PREFERRED_PORT = (
    "/dev/serial/by-id/"
    "usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_"
    "5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
)
FALLBACK_PORT = "/dev/ttyUSB0"
LOG_DIR = (
    Path(__file__).resolve().parents[3]
    / "runtime/core/calibration/logs"
)
BASE_STEPS = {0.01, 0.05}
GRIPPER_PRESETS = {
    "open": 1.6,
    "light": 2.0,
    "firm": 2.4,
    "pinch": 2.8,
}


class VerificationError(RuntimeError):
    """Fail-closed verification error."""


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
        timeout_s=1.5,
        settle_s=0.5,
        sleep_fn=time.sleep,
    ):
        self.transport = transport
        self.log = log
        self.timeout_s = float(timeout_s)
        self.settle_s = float(settle_s)
        if (
            not math.isfinite(self.timeout_s)
            or self.timeout_s <= 0
            or not math.isfinite(self.settle_s)
            or self.settle_s < 0
        ):
            raise ValueError(
                "timeout must be positive; settle time must be non-negative"
            )
        self.sleep_fn = sleep_fn
        self.started = False
        self.torque_enabled = False
        self.motion_blocked = False
        self.current_state = None
        self.pending_confirmation = None
        self.last_base_confirmation = None
        self.base_candidates = {
            "negative_limit": None,
            "positive_limit": None,
        }
        self.gripper_results = {}
        self._closed = False

    def _write_fixed(self, packet, purpose):
        self.log.record("command", purpose=purpose, packet=packet)
        payload = (
            json.dumps(packet, separators=(",", ":")) + "\n"
        ).encode("ascii")
        self.transport.write(payload)
        flush = getattr(self.transport, "flush", None)
        if flush is not None:
            flush()

    def _request_state(self, purpose):
        reset = getattr(self.transport, "reset_input_buffer", None)
        if reset is not None:
            reset()
        self._write_fixed({"T": 105}, purpose)

        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            try:
                raw = self.transport.readline()
            except Exception as exc:
                self.log.record(
                    "readback_failed", purpose=purpose, error=str(exc)
                )
                raise VerificationError("T105_READBACK_FAILED") from exc
            if not raw:
                continue
            try:
                packet = json.loads(
                    raw.decode("utf-8", errors="strict").strip()
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(packet, dict) or packet.get("T") != 1051:
                continue
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

        self.log.record(
            "readback_failed", purpose=purpose, error="T1051 timeout"
        )
        raise VerificationError("T105_READBACK_TIMEOUT")

    def startup(self):
        if self.started:
            raise VerificationError("SESSION_ALREADY_STARTED")
        state = self._request_state("startup_state")
        self.current_state = state
        self.started = True
        self.log.record("initial_state", state=state)
        return state

    def enable_torque(self):
        self._require_started()
        if self.motion_blocked:
            raise VerificationError("MOTION_BLOCKED_RECOVERY_REQUIRED")
        self._write_fixed({"T": 210, "cmd": 1}, "enable_torque")
        self.torque_enabled = True
        self.log.record("torque_enabled")

    def disable_torque(self):
        try:
            self._write_fixed({"T": 210, "cmd": 0}, "disable_torque")
            self.log.record("torque_disabled")
        finally:
            self.torque_enabled = False

    def recover_readback(self):
        self._require_started()
        state = self._request_state("explicit_readback_recovery")
        self.current_state = state
        self.motion_blocked = False
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
        self._write_fixed(
            {
                "T": 101,
                "joint": joint_id,
                "rad": float(target),
                "spd": 50,
                "acc": 0,
            },
            purpose,
        )
        self.sleep_fn(self.settle_s)
        try:
            state = self._request_state(f"{purpose}_readback")
        except VerificationError:
            self.motion_blocked = True
            self.log.record(
                "motion_blocked",
                reason="POST_MOTION_READBACK_FAILED",
                purpose=purpose,
                commanded_target=target,
            )
            try:
                self.disable_torque()
            except Exception as exc:
                self.log.record(
                    "torque_disable_failed", error=str(exc)
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
        }

    def shutdown(self):
        if self._closed:
            return
        try:
            try:
                self.disable_torque()
            except Exception as exc:
                self.log.record(
                    "torque_disable_failed", error=str(exc)
                )
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
        self._require_started()
        if self.motion_blocked:
            raise VerificationError("MOTION_BLOCKED_RECOVERY_REQUIRED")
        if not self.torque_enabled:
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
        output("\nCtrl+C received; disabling torque and exiting.")
    finally:
        session.shutdown()
        output("Final verification summary:")
        output(json.dumps(session.summary(), indent=2))
        output(f"Log: {session.log.path}")


def _open_serial():
    import os
    import serial

    port = PREFERRED_PORT if os.path.exists(PREFERRED_PORT) else FALLBACK_PORT
    transport = serial.Serial(
        port, BAUD, timeout=0.2, dsrdtr=None
    )
    transport.setRTS(False)
    transport.setDTR(False)
    return transport


def main():
    log = CalibrationLog()
    transport = _open_serial()
    session = BaseGripperVerification(transport, log)
    run_interactive(session)


if __name__ == "__main__":
    main()
