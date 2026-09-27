"""Offline checks for allowlisted pattern commands. No arm connection."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from runtime.core.safety.existing_motions import READY_TARGETS
from runtime.core.safety.pattern_commands import (
    LOCAL_EXECUTION_ENV,
    TRAJECTORY_PI_IP,
    TRAJECTORY_RELEASE_WAIT_S,
    TRAJECTORY_UDP_PORT,
    dispatch_pattern_command,
    execute_pattern_locally,
    format_inventory,
    lesson_serial_profile,
    main,
    pattern_pi_entry_scope,
    pattern_transport,
    trajectory_datagram,
)
from runtime.core.safety.pattern_registry import (
    REGISTRY,
    command_inventory,
    lissajous_steps,
    spiral_steps,
)


def _repository_root():
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        marker = candidate / "runtime" / "core" / "safety" / "production_motion.py"
        if marker.is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = _repository_root()
GOOD_ROUTE = "192.168.4.1 dev wlan0 src 192.168.4.2 uid 1000 cache"
FRESH = {"connected": True, "fresh": True}


class FakeClient:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at
        self.closed = False

    def _get(self, packet):
        if self.fail_at is not None and len(self.calls) + 1 == self.fail_at:
            raise ConnectionError("down")
        self.calls.append(packet)
        if packet.get("T") == 105:
            last = next(
                (
                    item for item in reversed(self.calls)
                    if item.get("T") == 101
                ),
                None,
            )
            base = 0.0 if last is None else last["rad"]
            return {"T": 1051, "b": base}
        return {"T": 1051}

    def close(self):
        self.closed = True


class FakeUdp:
    def __init__(self, fail_at=None):
        self.sent = []
        self.connected = None
        self.blocking = None
        self.closed = False
        self.fail_at = fail_at
        self.reads = 0
        self.bound = None

    def bind(self, address):
        self.bound = address

    def setblocking(self, flag):
        self.blocking = flag

    def connect(self, address):
        self.connected = address

    def send(self, payload):
        if self.fail_at is not None and len(self.sent) + 1 == self.fail_at:
            raise BlockingIOError()
        self.sent.append(payload)
        return len(payload)

    def recv(self, _size):
        self.reads += 1
        raise AssertionError("udp read")

    def close(self):
        self.closed = True


class PatternCommandTests(unittest.TestCase):
    def test_inventory_is_the_allowlist(self):
        names = [item["name"] for item in command_inventory()]
        self.assertEqual(
            names,
            [
                "lissajous", "circle", "spiral", "candle", "ready", "home",
                "observe_center", "observe_left", "observe_right",
                "scan_area", "scan_left", "scan_right",
            ],
        )
        self.assertIn("lissajous", format_inventory())
        self.assertNotIn("circle_path", format_inventory())
        self.assertNotIn("serial", format_inventory())

    def test_lissajous_points_come_from_the_lesson_script(self):
        steps = lissajous_steps(ROOT)
        packets = [step[1] for step in steps if step[0] == "packet"]
        stream = [packet for packet in packets if packet["T"] == 1041]
        self.assertEqual(packets[0], {"T": 210, "cmd": 1})
        self.assertEqual(packets[1]["T"], 104)
        self.assertEqual(packets[1]["x"], 240.0)
        self.assertEqual(len(stream), 301)
        self.assertEqual(
            stream[0],
            {
                "T": 1041, "x": 265.0, "y": 0.0, "z": 250.0,
                "t": 0.3, "r": 0, "g": 3.0,
            },
        )
        self.assertEqual(packets[-1]["T"], 104)
        self.assertEqual(packets[-1]["z"], 400)
        text = (
            ROOT / "lessons/01_trajectory_and_gripper/demo_lissajous.py"
        ).read_text(encoding="utf-8")
        self.assertIn("serial.Serial", text)
        self.assertNotIn("import serial", Path(
            ROOT / "runtime/core/safety/pattern_registry.py"
        ).read_text(encoding="utf-8"))

    def test_spiral_keeps_both_passes(self):
        packets = [
            step[1] for step in spiral_steps(ROOT) if step[0] == "packet"
        ]
        stream = [packet for packet in packets if packet["T"] == 1041]
        self.assertEqual(len(stream), 720)
        self.assertEqual(stream[0]["x"], 240.0 + 120.0)
        self.assertEqual(packets[-1], {"T": 105})

    def test_candle_packet_is_the_lesson_dict(self):
        from runtime.core.safety.pattern_registry import candle_steps

        packets = [
            step[1] for step in candle_steps(ROOT) if step[0] == "packet"
        ]
        self.assertEqual(packets[0], {"T": 210, "cmd": 1})
        self.assertEqual(
            packets[1],
            {
                "T": 102, "base": 0, "shoulder": 0, "elbow": 0,
                "wrist": 0, "roll": 0, "spd": 0, "acc": 0,
            },
        )
        self.assertNotIn("hand", packets[1])

    def test_ready_packet_matches_the_recorded_pose(self):
        from tempfile import TemporaryDirectory
        from runtime.core.safety.pattern_registry import ready_steps

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / REGISTRY["ready"]["source"]
            path.parent.mkdir(parents=True)
            path.write_text(
                textwrap.dedent(
                    """
                    cmd = {
                        "T": 102,
                        "base": 0.001533981,
                        "shoulder": -0.832951568,
                        "elbow": 2.399145952,
                        "wrist": 0.004601942,
                        "roll": 0.0,
                        "hand": 3.163068385,
                        "spd": 0,
                        "acc": 0,
                    }
                    """
                ),
                encoding="utf-8",
            )
            packet = [
                step[1] for step in ready_steps(tmp) if step[0] == "packet"
            ][0]
        self.assertEqual(packet["base"], READY_TARGETS["base"])
        self.assertEqual(packet["hand"], READY_TARGETS["hand"])
        self.assertEqual(packet["spd"], 0)

    def test_circle_and_scan_use_source_constants(self):
        from tempfile import TemporaryDirectory
        from runtime.core.safety.pattern_registry import (
            circle_steps,
            scan_area_steps,
        )

        with TemporaryDirectory() as tmp:
            circle = Path(tmp) / REGISTRY["circle"]["source"]
            circle.parent.mkdir(parents=True)
            circle.write_text(
                textwrap.dedent(
                    """
                    CX, CY, CZ = 235.0, 0.0, 234.0
                    R = 100.0
                    AMP = 20.0
                    STEPS = 180
                    REVOLUTIONS = 3
                    DT = 0.04
                    GRIPPER_CMD = 3.0
                    START_POSE = {"x": 285.0, "y": 0.0, "z": 234.0, "t": 0.0, "r": 0.0, "g": 3.0, "spd": 0.6}
                    CANDLE_POSE = {"x": 48.9, "y": 0.0, "z": 552.6, "t": -1.56, "r": -0.0015, "g": 3.0, "spd": 0.6}
                    """
                ),
                encoding="utf-8",
            )
            scan = Path(tmp) / REGISTRY["scan_area"]["source"]
            scan.parent.mkdir(parents=True)
            scan.write_text(
                "CENTER_BASE = 0.001533981\n"
                "LEFT_BASE = 1.610679827\n"
                "RIGHT_BASE = -1.578466231\n"
                "BASE_SPEED = 200\n"
                "BASE_ACCEL = 10\n",
                encoding="utf-8",
            )
            circle_packets = [
                step[1] for step in circle_steps(tmp) if step[0] == "packet"
            ]
            stream = [
                packet for packet in circle_packets if packet["T"] == 1041
            ]
            self.assertEqual(len(stream), 540)
            self.assertEqual(stream[0]["x"], 335.0)
            self.assertEqual(stream[0]["z"], 234.0)
            moves = [
                step[1]["rad"]
                for step in scan_area_steps(tmp)
                if step[0] == "packet" and step[1]["T"] == 101
            ]
            self.assertEqual(
                moves,
                [0.001533981, 1.610679827, -1.578466231, 0.001533981],
            )

    def test_circle_resolves_gripper_name_and_signed_pose(self):
        from runtime.core.safety.pattern_registry import circle_steps

        with tempfile.TemporaryDirectory() as tmp:
            circle = Path(tmp) / REGISTRY["circle"]["source"]
            circle.parent.mkdir(parents=True)
            circle.write_text(
                textwrap.dedent(
                    """
                    CX, CY, CZ = 235.0, 0.0, 234.0
                    R = 100.0
                    AMP = 20.0
                    STEPS = 180
                    REVOLUTIONS = 3
                    DT = 0.04
                    GRIPPER_CMD = 3.0
                    START_POSE = {
                        "x": 285.0, "y": 0.0, "z": 234.0,
                        "t": 0.0, "r": 0.0, "g": GRIPPER_CMD, "spd": 0.6,
                    }
                    CANDLE_POSE = {
                        "x": 48.9, "y": 0.0, "z": 552.6,
                        "t": -1.56, "r": -0.0015, "g": GRIPPER_CMD, "spd": 0.6,
                    }
                    """
                ),
                encoding="utf-8",
            )
            packets = [
                step[1] for step in circle_steps(tmp) if step[0] == "packet"
            ]
        stream = [packet for packet in packets if packet["T"] == 1041]
        self.assertEqual(len(stream), 540)
        self.assertEqual(stream[0]["x"], 335.0)
        self.assertEqual(stream[0]["g"], 3.0)
        self.assertEqual(stream[0]["t"], 0.0)
        setup = [packet for packet in packets if packet["T"] == 104]
        self.assertEqual(setup[0]["x"], 285.0)
        self.assertEqual(setup[0]["g"], 3.0)
        self.assertEqual(setup[0]["spd"], 0.6)
        self.assertEqual(setup[1]["z"], 552.6)
        self.assertEqual(setup[1]["t"], -1.56)
        self.assertEqual(setup[1]["r"], -0.0015)
        self.assertEqual(setup[1]["g"], 3.0)

    def test_circle_streams_when_named_poses_are_absent(self):
        from runtime.core.safety.pattern_registry import circle_steps

        with tempfile.TemporaryDirectory() as tmp:
            circle = Path(tmp) / REGISTRY["circle"]["source"]
            circle.parent.mkdir(parents=True)
            circle.write_text(
                "CX, CY, CZ = 235.0, 0.0, 234.0\n"
                "R = 100.0\nAMP = 20.0\nSTEPS = 180\n"
                "REVOLUTIONS = 3\nDT = 0.04\nGRIPPER_CMD = 3.0\n",
                encoding="utf-8",
            )
            packets = [
                step[1] for step in circle_steps(tmp) if step[0] == "packet"
            ]
        self.assertEqual(
            [packet["T"] for packet in packets if packet["T"] == 104],
            [],
        )
        self.assertEqual(
            sum(1 for packet in packets if packet["T"] == 1041),
            540,
        )

    def _run(
        self,
        pattern,
        root,
        client,
        reader=None,
        route=GOOD_ROUTE,
        udp_socket_factory=None,
        sleep_fn=None,
        clock=None,
        stream_id_factory=None,
    ):
        holder = {}
        sleeps = []

        def factory():
            holder["built"] = holder.get("built", 0) + 1
            return client

        def record_sleep(seconds):
            sleeps.append(seconds)

        with tempfile.TemporaryDirectory() as runtime:
            with pattern_pi_entry_scope():
                result = execute_pattern_locally(
                    ["run", pattern],
                    route_text=route,
                    state_reader=reader or (lambda: dict(FRESH)),
                    sleep_fn=record_sleep if sleep_fn is None else sleep_fn,
                    clock=clock or (lambda: 0.0),
                    transport_factory=factory,
                    pattern_root=root,
                    runtime_dir=runtime,
                    pid_alive=lambda _pid: False,
                    udp_socket_factory=udp_socket_factory,
                    stream_id_factory=stream_id_factory,
                )
            status_path = Path(runtime) / "transport-status.json"
            if status_path.is_file():
                result["transport_status"] = json.loads(
                    status_path.read_text(encoding="utf-8")
                )
        result["factory_calls"] = holder.get("built", 0)
        result["sleeps"] = sleeps
        return result

    def test_wrong_route_sends_nothing(self):
        def reader():
            raise AssertionError("T105")

        result = self._run(
            "candle",
            ROOT,
            FakeClient(),
            reader=reader,
            route="192.168.4.1 via 192.168.1.1 dev eth0 src 192.168.4.2",
        )
        self.assertEqual(result["reason"], "ARM_ROUTE_WRONG_INTERFACE")
        self.assertEqual(result["hardware_action"], "NONE")
        self.assertEqual(result["factory_calls"], 0)

    def test_failed_preflight_sends_nothing(self):
        calls = []

        def reader():
            calls.append("read")
            raise ConnectionError("no t105")

        client = FakeClient()
        result = self._run("candle", ROOT, client, reader=reader)
        self.assertEqual(result["reason"], "PREFLIGHT_UNAVAILABLE")
        self.assertEqual(result["preflight_attempts"], 5)
        self.assertEqual(len(calls), 5)
        self.assertEqual(client.calls, [])
        self.assertEqual(result["factory_calls"], 0)

    def test_stale_t105_sends_nothing(self):
        client = FakeClient()
        result = self._run(
            "candle",
            ROOT,
            client,
            reader=lambda: {"connected": True, "fresh": False},
        )
        self.assertEqual(result["reason"], "PREFLIGHT_UNAVAILABLE")
        self.assertEqual(client.calls, [])

    def test_http_failure_stops_the_session(self):
        client = FakeClient(fail_at=2)
        result = self._run("candle", ROOT, client)
        self.assertEqual(result["transport"], "http")
        self.assertFalse(result["serial_opened"])
        self.assertEqual(result["reason"], "PATTERN_HTTP_FAILED")
        self.assertEqual(result["hardware_action"], "PATTERN_OUTCOME_UNCERTAIN")
        self.assertEqual([packet["T"] for packet in client.calls], [210])
        self.assertEqual(result["factory_calls"], 1)
        self.assertTrue(client.closed)

    def test_scan_area_reuses_one_client_for_every_point(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / REGISTRY["scan_area"]["source"]
            path.parent.mkdir(parents=True)
            path.write_text(
                "CENTER_BASE = 0.001533981\n"
                "LEFT_BASE = 1.610679827\n"
                "RIGHT_BASE = -1.578466231\n"
                "BASE_SPEED = 200\n"
                "BASE_ACCEL = 10\n",
                encoding="utf-8",
            )
            client = FakeClient()
            result = self._run("scan_area", tmp, client)
        moves = [packet for packet in client.calls if packet["T"] == 101]
        self.assertTrue(result["ok"])
        self.assertEqual(result["factory_calls"], 1)
        self.assertEqual(
            [packet["rad"] for packet in moves],
            [0.001533981, 1.610679827, -1.578466231, 0.001533981],
        )
        self.assertEqual(moves[0]["spd"], 200)
        self.assertEqual(moves[0]["acc"], 10)
        self.assertGreaterEqual(
            sum(1 for packet in client.calls if packet["T"] == 105),
            4,
        )

    def test_stop_file_blocks_the_next_point(self):
        client = FakeClient()
        original = client._get

        with tempfile.TemporaryDirectory() as runtime_name:
            runtime = Path(runtime_name)

            def _get(packet):
                response = original(packet)
                (runtime / "stop").write_text("stop\n", encoding="utf-8")
                return response

            client._get = _get
            with pattern_pi_entry_scope():
                result = execute_pattern_locally(
                    ["run", "candle"],
                    route_text=GOOD_ROUTE,
                    state_reader=lambda: dict(FRESH),
                    sleep_fn=lambda _seconds: None,
                    clock=lambda: 0.0,
                    transport_factory=lambda: client,
                    pattern_root=ROOT,
                    runtime_dir=runtime,
                    pid_alive=lambda _pid: False,
                )
        self.assertEqual(result["reason"], "PATTERN_STOP_REQUESTED")
        self.assertEqual(result["torque_off_sent"], False)
        self.assertEqual(
            [packet["T"] for packet in client.calls if packet["T"] != 105],
            [210],
        )
        self.assertEqual(result["final_t105"]["T"], 1051)

    def test_local_call_does_not_open_http(self):
        def factory():
            raise AssertionError("http")

        result = execute_pattern_locally(
            ["run", "lissajous"],
            transport_factory=factory,
            state_reader=lambda: (_ for _ in ()).throw(AssertionError("t105")),
        )
        self.assertEqual(result["reason"], "LOCAL_PATTERN_REFUSED")
        self.assertEqual(result["hardware_action"], "NONE")

    def test_list_and_unknown_do_not_ssh(self):
        def runner(*_args, **_kwargs):
            raise AssertionError("ssh")

        listed = dispatch_pattern_command(["list"], runner=runner)
        unknown = dispatch_pattern_command(["run", "nope"], runner=runner)
        self.assertTrue(listed["ok"])
        self.assertEqual(len(listed["patterns"]), 12)
        self.assertEqual(unknown["reason"], "UNKNOWN_PATTERN_COMMAND")
        self.assertEqual(unknown["hardware_action"], "NONE")

    def test_run_dispatch_stays_on_the_pi(self):
        calls = []

        def runner(args, input_bytes=None, timeout_s=180):
            calls.append((args, input_bytes, timeout_s))
            if input_bytes is not None:
                return subprocess.CompletedProcess(args, 0, b"", b"")
            body = json.dumps(
                {"ok": True, "hardware_action": "PATTERN_HTTP_SENT"}
            ).encode()
            return subprocess.CompletedProcess(args, 0, body, b"")

        result = dispatch_pattern_command(
            ["run", "lissajous"], runner=runner, on_pi=False
        )
        self.assertEqual(result["hardware_action"], "PATTERN_HTTP_SENT")
        self.assertEqual(len(calls), 2)
        remote = calls[1][0][7]
        self.assertIn(f"{LOCAL_EXECUTION_ENV}=1", remote)
        self.assertIn("pattern_command_pi_entry.py run lissajous", remote)
        self.assertNotIn("192.168.4.1", remote)

    def test_direct_pi_cli_does_not_invoke_ssh(self):
        def runner(*_args, **_kwargs):
            raise AssertionError("ssh")

        opened = []

        def factory():
            sock = FakeUdp()
            opened.append(sock)
            return sock

        client = FakeClient()
        with tempfile.TemporaryDirectory() as runtime:
            result = dispatch_pattern_command(
                ["run", "lissajous"],
                runner=runner,
                on_pi=True,
                route_text=GOOD_ROUTE,
                state_reader=lambda: dict(FRESH),
                sleep_fn=lambda _seconds: None,
                clock=lambda: 0.0,
                transport_factory=lambda: client,
                pattern_root=ROOT,
                runtime_dir=runtime,
                pid_alive=lambda _pid: False,
                udp_socket_factory=factory,
            )
        self.assertEqual(result["reason"], "PATTERN_FINISHED")
        self.assertEqual(result["transport"], "udp")
        self.assertEqual(result["hardware_action"], "PATTERN_UDP_SENT")
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened[0].connected, ("192.168.4.1", TRAJECTORY_UDP_PORT))
        self.assertEqual(opened[0].bound, (TRAJECTORY_PI_IP, 0))
        self.assertFalse(result["serial_opened"])
        self.assertTrue(result["udp_opened"])
        self.assertEqual(result["preflight_fresh"], True)
        self.assertEqual(
            [packet["T"] for packet in client.calls],
            [210, 104, 104, 105],
        )
        self.assertEqual(len(opened[0].sent), 301)
        self.assertEqual(result["motion_packets_sent"], 304)
        self.assertEqual(opened[0].reads, 0)

    def test_stop_does_not_send_torque_off(self):
        signaled = []
        client = FakeClient()
        with tempfile.TemporaryDirectory() as runtime_name:
            pid_path = Path(runtime_name) / "pattern.pid"
            pid_path.write_text("4242", encoding="utf-8")
            with pattern_pi_entry_scope():
                result = execute_pattern_locally(
                    ["stop"],
                    route_text="192.168.4.1 dev eth0 src 192.168.4.2",
                    transport_factory=lambda: (_ for _ in ()).throw(
                        AssertionError("stop opened http")
                    ),
                    runtime_dir=runtime_name,
                    pid_alive=lambda _pid: True,
                    signal_pid=lambda pid: signaled.append(pid),
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "STOP_REQUESTED")
        self.assertEqual(result["hardware_action"], "NONE")
        self.assertFalse(result["torque_off_sent"])
        self.assertEqual(signaled, [4242])
        self.assertEqual(client.calls, [])

    def test_torque_off_is_explicit_and_route_gated(self):
        client = FakeClient()
        with pattern_pi_entry_scope():
            refused = execute_pattern_locally(
                ["torque-off"],
                route_text="192.168.4.1 dev eth0 src 192.168.4.2",
                transport_factory=lambda: client,
            )
            sent = execute_pattern_locally(
                ["torque-off"],
                route_text=GOOD_ROUTE,
                transport_factory=lambda: client,
            )
        self.assertEqual(refused["reason"], "ARM_ROUTE_WRONG_INTERFACE")
        self.assertFalse(refused["torque_off_sent"])
        self.assertEqual(sent["hardware_action"], "TORQUE_OFF_SENT")
        self.assertEqual(client.calls, [{"T": 210, "cmd": 0}])

    def test_entry_refuses_without_the_pi_marker(self):
        entry = (
            ROOT
            / "runtime/core/safety/pattern_command_pi_entry.py"
        )
        env = os.environ.copy()
        env.pop(LOCAL_EXECUTION_ENV, None)
        completed = subprocess.run(
            [sys.executable, str(entry), "run", "candle"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("No hardware request was sent", completed.stderr)
        self.assertNotIn("192.168.4.1", completed.stdout + completed.stderr)

    def test_lissajous_streams_existing_points_over_udp(self):
        self.assertEqual(pattern_transport("lissajous"), "udp")
        self.assertEqual(pattern_transport("circle"), "udp")
        self.assertEqual(pattern_transport("spiral"), "udp")
        self.assertEqual(pattern_transport("candle"), "http")
        self.assertEqual(pattern_transport("ready"), "http")
        self.assertEqual(pattern_transport("observe_center"), "http")
        self.assertEqual(pattern_transport("home"), "http")

        class Clock:
            def __init__(self):
                self.now = 0.0
                self.sleeps = []

            def __call__(self):
                return self.now

            def sleep(self, seconds):
                self.sleeps.append(seconds)
                self.now += float(seconds)

        clock = Clock()
        sock = FakeUdp()
        client = FakeClient()
        result = self._run(
            "lissajous",
            ROOT,
            client,
            udp_socket_factory=lambda: sock,
            sleep_fn=clock.sleep,
            clock=clock,
            stream_id_factory=lambda: 7,
        )
        envelopes = [json.loads(item.decode("utf-8")) for item in sock.sent]
        commands = [item["cmd"] for item in envelopes]
        self.assertEqual(result["transport"], "udp")
        self.assertTrue(result["udp_opened"])
        self.assertFalse(result["serial_opened"])
        self.assertEqual(result["udp_target"], {"host": "192.168.4.1", "port": 4210})
        self.assertEqual(result["udp_stream_id"], 7)
        self.assertEqual(result["reason"], "PATTERN_FINISHED")
        self.assertEqual(result["hardware_action"], "PATTERN_UDP_SENT")
        self.assertIs(sock.blocking, False)
        self.assertEqual(sock.bound, (TRAJECTORY_PI_IP, 0))
        self.assertEqual(sock.connected, ("192.168.4.1", TRAJECTORY_UDP_PORT))
        self.assertTrue(sock.closed)
        self.assertEqual(sock.reads, 0)
        self.assertEqual(clock.sleeps[0], 0.5)
        self.assertEqual(clock.sleeps[1], 2.0)
        gaps = [delay for delay in clock.sleeps if abs(delay - 0.03) < 1e-9]
        self.assertEqual(len(gaps), 300)
        self.assertIn(TRAJECTORY_RELEASE_WAIT_S, clock.sleeps)
        self.assertEqual(clock.sleeps[-1], 2.0)
        self.assertEqual(len(commands), 301)
        self.assertEqual([item["seq"] for item in envelopes], list(range(301)))
        self.assertEqual({item["sid"] for item in envelopes}, {7})
        self.assertEqual(
            commands[0],
            {
                "T": 1041, "x": 265.0, "y": 0.0, "z": 250.0,
                "t": 0.3, "r": 0, "g": 3.0,
            },
        )
        self.assertEqual(sock.sent[0], trajectory_datagram(commands[0], 7, 0))
        self.assertFalse(any(item.endswith(b"\n") for item in sock.sent))
        self.assertTrue(all(item["cmd"]["T"] == 1041 for item in envelopes))
        self.assertEqual(
            [packet["T"] for packet in client.calls],
            [210, 104, 104, 105],
        )
        self.assertEqual(client.calls[1]["z"], 250)
        self.assertEqual(client.calls[2]["z"], 400)
        self.assertEqual(result["final_t105"]["T"], 1051)
        self.assertFalse(result["torque_off_sent"])
        status = result["transport_status"]
        self.assertEqual(status["transport_state"], "idle")
        self.assertFalse(status["active"])
        self.assertEqual(status["stream_id"], 7)
        self.assertEqual(status["last_sequence"], 300)
        self.assertEqual(status["last_completion"]["pattern"], "lissajous")
        self.assertEqual(status["last_completion"]["sequence"], 300)
        self.assertEqual(status["udp_target"], "192.168.4.1:4210")
        self.assertFalse(status["serial_fallback"])
        self.assertNotEqual(status["transport_state"], "serial")

    def test_udp_lateness_aborts_without_bursting(self):
        class Clock:
            def __init__(self):
                self.now = 0.0

            def __call__(self):
                return self.now

            def sleep(self, seconds):
                self.now += float(seconds)

        clock = Clock()
        sock = FakeUdp()

        def send(payload):
            sock.sent.append(payload)
            if len(sock.sent) == 1:
                clock.now += 0.10
            return len(payload)

        sock.send = send
        result = self._run(
            "lissajous",
            ROOT,
            FakeClient(),
            udp_socket_factory=lambda: sock,
            sleep_fn=clock.sleep,
            clock=clock,
            stream_id_factory=lambda: 9,
        )
        self.assertEqual(result["reason"], "PATTERN_UDP_LATE")
        self.assertEqual(len(sock.sent), 1)
        self.assertEqual(json.loads(sock.sent[0])["seq"], 0)
        self.assertEqual(result["hardware_action"], "PATTERN_OUTCOME_UNCERTAIN")
        self.assertEqual(result["final_t105"]["T"], 1051)
        status = result["transport_status"]
        self.assertEqual(status["transport_state"], "idle")
        self.assertEqual(status["active_failure"], "PATTERN_UDP_LATE")
        self.assertEqual(status["stream_id"], 9)
        self.assertEqual(status["last_sequence"], 0)
        self.assertEqual(status["last_late"]["sequence"], 0)
        self.assertFalse(status["serial_fallback"])

    def test_udp_send_failure_stops_the_stream(self):
        sock = FakeUdp(fail_at=2)
        result = self._run(
            "lissajous",
            ROOT,
            FakeClient(),
            udp_socket_factory=lambda: sock,
        )
        self.assertEqual(result["reason"], "PATTERN_UDP_FAILED")
        self.assertEqual(len(sock.sent), 1)
        self.assertEqual(result["hardware_action"], "PATTERN_OUTCOME_UNCERTAIN")
        self.assertEqual(result["final_t105"]["T"], 1051)
        self.assertTrue(sock.closed)
        self.assertEqual(
            result["transport_status"]["active_failure"], "PATTERN_UDP_FAILED"
        )
        self.assertFalse(result["transport_status"]["serial_fallback"])

    def test_udp_stays_closed_when_preflight_fails(self):
        opened = []

        def factory():
            opened.append(True)
            return FakeUdp()

        result = self._run(
            "lissajous",
            ROOT,
            FakeClient(),
            reader=lambda: {"connected": True, "fresh": False},
            udp_socket_factory=factory,
        )
        self.assertEqual(result["transport"], "udp")
        self.assertFalse(result["udp_opened"])
        self.assertEqual(opened, [])
        self.assertEqual(result["reason"], "PREFLIGHT_UNAVAILABLE")
        self.assertEqual(result["factory_calls"], 0)
        self.assertNotIn("transport_status", result)

    def test_spiral_profile_matches_its_lesson_open(self):
        self.assertEqual(
            lesson_serial_profile(ROOT, "spiral"),
            {
                "port": "/dev/ttyUSB0",
                "baud": 115200,
                "timeout_s": 0.1,
                "settle_s": 2.0,
            },
        )
        delays = [
            step[2]
            for step in spiral_steps(ROOT)
            if step[0] == "packet" and step[1]["T"] == 1041
        ]
        self.assertEqual(delays, [0.03] * 720)

    def test_circle_profile_uses_its_own_serial_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            circle = Path(tmp) / REGISTRY["circle"]["source"]
            circle.parent.mkdir(parents=True)
            circle.write_text(
                "PORT = '/dev/ttyUSB0'\nBAUD = 115200\n"
                "def main():\n"
                "    ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.05)\n"
                "    time.sleep(0.5)\n"
                "    time.sleep(0.2)\n",
                encoding="utf-8",
            )
            self.assertEqual(
                lesson_serial_profile(tmp, "circle"),
                {
                    "port": "/dev/ttyUSB0",
                    "baud": 115200,
                    "timeout_s": 0.05,
                    "settle_s": 0.5,
                },
            )

    def test_command_modules_do_not_run_lesson_scripts(self):
        commands = (
            ROOT / "runtime/core/safety/pattern_commands.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("runpy", commands)
        self.assertNotIn("_TrajectoryLink", commands)
        self.assertNotIn("create_connection", commands)
        self.assertNotIn("import serial", commands)
        self.assertNotIn("serial.Serial(", commands)
        self.assertNotIn("LessonSerialLink", commands)
        self.assertNotIn("lesson_send_json", commands)
        self.assertNotIn('return "serial"', commands)
        self.assertIn("SOCK_DGRAM", commands)
        for relative in (
            "runtime/core/safety/pattern_registry.py",
            "runtime/core/safety/pattern_command_pi_entry.py",
            "roarm",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("serial.Serial", text)
            self.assertNotIn("runpy", text)


if __name__ == "__main__":
    unittest.main()
