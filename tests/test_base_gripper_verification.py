from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT
    / "milestones/Phase_1_System_Authority/02_mechanical_truth"
    / "milestone_02_base_gripper_verification.py"
)
SPEC = importlib.util.spec_from_file_location(
    "base_gripper_verification", TOOL_PATH
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class FakeTransport:
    def __init__(self, *, base=0.25, gripper=2.0):
        self.base = base
        self.gripper = gripper
        self.writes = []
        self.responses = []
        self.fail_next_feedback = False
        self.closed = False

    def reset_input_buffer(self):
        self.responses.clear()

    def write(self, payload):
        packet = json.loads(payload.decode("ascii"))
        self.writes.append(packet)
        if packet["T"] == 101:
            if packet["joint"] == 1:
                self.base = packet["rad"]
            elif packet["joint"] == 6:
                self.gripper = packet["rad"]
            else:
                raise AssertionError("unexpected joint")
        elif packet["T"] == 105:
            if self.fail_next_feedback:
                self.fail_next_feedback = False
                self.responses.append(RuntimeError("simulated read failure"))
            else:
                self.responses.append(
                    json.dumps(
                        {"T": 1051, "b": self.base, "g": self.gripper}
                    ).encode("ascii")
                )

    def flush(self):
        pass

    def readline(self):
        if not self.responses:
            return b""
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


class VerificationToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def session(self, transport=None):
        transport = transport or FakeTransport()
        log = tool.CalibrationLog(Path(self.temp.name))
        session = tool.BaseGripperVerification(
            transport, log, timeout_s=0.01, settle_s=0
        )
        return session, transport

    def started_session(self):
        session, transport = self.session()
        state = session.startup()
        self.assertEqual(state["base"], 0.25)
        self.assertEqual(state["gripper"], 2.0)
        return session, transport

    def test_startup_is_read_only_and_does_not_enable_torque(self):
        session, transport = self.started_session()
        self.assertEqual(transport.writes, [{"T": 105}])
        self.assertFalse(session.torque_enabled)
        session.shutdown()

    def test_base_jog_commands_only_joint_one(self):
        session, transport = self.started_session()
        session.enable_torque()
        result = session.jog_base(0.05)

        motion = [packet for packet in transport.writes if packet["T"] == 101]
        self.assertEqual(
            motion,
            [{"T": 101, "joint": 1, "rad": 0.3, "spd": 50, "acc": 0}],
        )
        self.assertAlmostEqual(result["reported"], 0.3)
        self.assertAlmostEqual(result["error"], 0.0)
        self.assertEqual(transport.gripper, 2.0)
        session.confirm_base(True, "clear")
        session.shutdown()

    def test_gripper_commands_only_joint_six(self):
        session, transport = self.started_session()
        session.enable_torque()
        result = session.move_gripper(2.4)

        motion = [packet for packet in transport.writes if packet["T"] == 101]
        self.assertEqual(
            motion,
            [{"T": 101, "joint": 6, "rad": 2.4, "spd": 50, "acc": 0}],
        )
        self.assertEqual(result["reported"], 2.4)
        self.assertEqual(transport.base, 0.25)
        session.shutdown()

    def test_gripper_rejects_values_outside_verified_presets(self):
        session, transport = self.started_session()
        session.enable_torque()
        for target in (1.59, 1.5, 2.9, 3.0):
            with self.subTest(target=target):
                with self.assertRaises(tool.VerificationError):
                    session.move_gripper(target)
        self.assertFalse(
            any(packet["T"] == 101 for packet in transport.writes)
        )
        session.shutdown()

    def test_failed_post_motion_readback_blocks_until_recovery(self):
        session, transport = self.started_session()
        session.enable_torque()
        transport.fail_next_feedback = True

        with self.assertRaisesRegex(
            tool.VerificationError, "T105_READBACK_FAILED"
        ):
            session.jog_base(0.01)
        self.assertTrue(session.motion_blocked)
        self.assertFalse(session.torque_enabled)
        self.assertIn({"T": 210, "cmd": 0}, transport.writes)
        with self.assertRaisesRegex(
            tool.VerificationError, "MOTION_BLOCKED_RECOVERY_REQUIRED"
        ):
            session.jog_base(0.01)

        recovered = session.recover_readback()
        self.assertEqual(recovered["base"], 0.26)
        self.assertFalse(session.motion_blocked)
        session.shutdown()

    def test_ctrl_c_path_attempts_torque_disable(self):
        session, transport = self.session()

        def interrupt(_prompt):
            raise KeyboardInterrupt

        tool.run_interactive(session, input_fn=interrupt, output=lambda _: None)
        self.assertIn({"T": 210, "cmd": 0}, transport.writes)
        self.assertFalse(
            any(
                packet == {"T": 210, "cmd": 1}
                for packet in transport.writes
            )
        )
        self.assertTrue(transport.closed)

    def test_log_files_are_unique_and_append_events(self):
        now = datetime(2026, 9, 25, tzinfo=timezone.utc)
        first = tool.CalibrationLog(Path(self.temp.name), now=now)
        second = tool.CalibrationLog(Path(self.temp.name), now=now)
        self.assertNotEqual(first.path, second.path)

        first.record("one", value=1)
        first.record("two", value=2)
        events = [
            json.loads(line)["event"]
            for line in first.path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(events, ["one", "two"])

    def test_existing_calibration_files_are_never_modified(self):
        paths = (
            ROOT / "runtime/core/calibration/joint_limits.json",
            ROOT / "runtime/core/calibration/gripper_map.json",
        )
        before = {path: path.read_bytes() for path in paths}

        session, _ = self.started_session()
        session.enable_torque()
        session.move_gripper(1.6)
        session.confirm_gripper(
            direction_ok=True,
            physical_opening="open",
            buzzing_or_stall=False,
            excessive_force=False,
            acceptable=True,
            note="fake transport",
        )
        session.shutdown()

        self.assertEqual(
            {path: path.read_bytes() for path in paths},
            before,
        )


if __name__ == "__main__":
    unittest.main()
