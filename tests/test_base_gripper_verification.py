from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse


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
        self.calls = []
        self.fail_next_feedback = False
        self.closed = False

    def read_state(self):
        self.calls.append({"T": 105})
        if self.fail_next_feedback:
            self.fail_next_feedback = False
            raise RuntimeError("simulated read failure")
        return {"T": 1051, "b": self.base, "g": self.gripper}

    def set_torque(self, enabled):
        packet = {"T": 210, "cmd": 1 if enabled else 0}
        self.calls.append(packet)
        return {"T": 210}

    def move_base(self, target):
        packet = {
            "T": 101,
            "joint": 1,
            "rad": float(target),
            "spd": 50,
            "acc": 0,
        }
        self.calls.append(packet)
        self.base = float(target)
        return {"T": 101}

    def move_gripper(self, target):
        packet = {
            "T": 101,
            "joint": 6,
            "rad": float(target),
            "spd": 50,
            "acc": 0,
        }
        self.calls.append(packet)
        self.gripper = float(target)
        return {"T": 101}

    def close(self):
        self.closed = True


class FakeHttpResponse:
    def __init__(self, packet):
        self.payload = json.dumps(packet).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class VerificationToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def session(self, transport=None):
        transport = transport or FakeTransport()
        log = tool.CalibrationLog(Path(self.temp.name))
        session = tool.BaseGripperVerification(
            transport, log, settle_s=0
        )
        return session, transport

    def started_session(self):
        session, transport = self.session()
        state = session.startup()
        self.assertEqual(state["base"], 0.25)
        self.assertEqual(state["gripper"], 2.0)
        return session, transport

    def test_http_transport_reuses_proven_url_pattern(self):
        requests = []

        def fake_urlopen(url, timeout):
            parsed = urlparse(url)
            command = json.loads(parse_qs(parsed.query)["json"][0])
            requests.append((parsed, command, timeout))
            if command["T"] == 105:
                return FakeHttpResponse(
                    {"T": 1051, "b": 0.25, "g": 2.0}
                )
            return FakeHttpResponse({"T": command["T"]})

        transport = tool.RoArmHttpTransport(
            "http://192.168.4.1/",
            urlopen_fn=fake_urlopen,
        )
        transport.read_state()
        transport.set_torque(True)
        transport.move_base(0.3)
        transport.move_gripper(2.4)
        transport.set_torque(False)

        self.assertEqual(
            [command for _, command, _ in requests],
            [
                {"T": 105},
                {"T": 210, "cmd": 1},
                {
                    "T": 101,
                    "joint": 1,
                    "rad": 0.3,
                    "spd": 50,
                    "acc": 0,
                },
                {
                    "T": 101,
                    "joint": 6,
                    "rad": 2.4,
                    "spd": 50,
                    "acc": 0,
                },
                {"T": 210, "cmd": 0},
            ],
        )
        for parsed, _, timeout in requests:
            self.assertEqual(parsed.scheme, "http")
            self.assertEqual(parsed.netloc, "192.168.4.1")
            self.assertEqual(parsed.path, "/js")
            self.assertEqual(timeout, 1.5)

    def test_tool_has_no_serial_or_generic_command_api(self):
        source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import serial", source)
        self.assertNotIn("send_command", source)
        public = {
            name
            for name in dir(tool.RoArmHttpTransport)
            if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {"move_base", "move_gripper", "read_state", "set_torque"},
        )

    def test_startup_is_read_only_and_does_not_enable_torque(self):
        session, transport = self.started_session()
        self.assertEqual(transport.calls, [{"T": 105}])
        self.assertFalse(session.torque_enabled)
        session.shutdown()

    def test_base_jog_commands_only_joint_one(self):
        session, transport = self.started_session()
        session.enable_torque()
        result = session.jog_base(0.05)

        motion = [packet for packet in transport.calls if packet["T"] == 101]
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

        motion = [packet for packet in transport.calls if packet["T"] == 101]
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
            any(packet["T"] == 101 for packet in transport.calls)
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
        self.assertIn({"T": 210, "cmd": 0}, transport.calls)
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
        self.assertIn({"T": 210, "cmd": 0}, transport.calls)
        self.assertFalse(
            any(
                packet == {"T": 210, "cmd": 1}
                for packet in transport.calls
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
