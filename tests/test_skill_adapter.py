"""Offline adapter checks. No arm connection and no UDP socket."""
import tempfile
import unittest
from pathlib import Path

from runtime.core.safety.pattern_commands import pattern_pi_entry_scope
from runtime.core.safety.skill_adapter import engineering, move_pose, run_named, stop_motion

GOOD_ROUTE = "192.168.4.1 dev wlan0 src 192.168.4.2 uid 1000 cache"
FRESH = {"connected": True, "fresh": True}


class FakeClient:
    def __init__(self):
        self.calls = []
        self.closed = False

    def _get(self, packet):
        self.calls.append(packet)
        if packet.get("T") == 105:
            return {"T": 1051, "b": 0.0}
        return {"T": 1051}

    def close(self):
        self.closed = True


class SkillAdapterTests(unittest.TestCase):
    def test_move_pose_is_one_http_t104(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as runtime:
            with pattern_pi_entry_scope():
                result = move_pose(
                    {"x": 10, "y": -5, "z": 250},
                    route_text=GOOD_ROUTE,
                    state_reader=lambda: dict(FRESH),
                    sleep_fn=lambda _seconds: None,
                    clock=lambda: 0.0,
                    transport_factory=lambda: client,
                    runtime_dir=runtime,
                    pid_alive=lambda _pid: False,
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["transport"], "http")
        self.assertFalse(result["udp_opened"])
        self.assertFalse(result["serial_opened"])
        motion = [item for item in client.calls if item.get("T") == 104]
        self.assertEqual(len(motion), 1)
        self.assertEqual(motion[0]["x"], 10.0)
        self.assertEqual(motion[0]["z"], 250.0)
        self.assertEqual(motion[0]["spd"], 0.5)
        self.assertFalse(any(item.get("T") == 1041 for item in client.calls))

    def test_named_run_and_stop_delegate_without_opening_udp_here(self):
        seen = []

        def fake_execute(argv, **_options):
            seen.append(list(argv))
            return {"ok": True, "command": argv[0], "reason": "STUB"}

        import runtime.core.safety.skill_adapter as adapter

        original = adapter.execute_pattern_locally
        adapter.execute_pattern_locally = fake_execute
        try:
            self.assertTrue(run_named("home")["ok"])
            self.assertTrue(stop_motion()["ok"])
        finally:
            adapter.execute_pattern_locally = original
        self.assertEqual(seen, [["run", "home"], ["stop"]])

    def test_engineering_rejects_udp_trajectory_packets(self):
        with tempfile.TemporaryDirectory() as runtime:
            result = engineering(
                {"T": 1041, "x": 0, "y": 0, "z": 0},
                route_text=GOOD_ROUTE,
                state_reader=lambda: dict(FRESH),
                sleep_fn=lambda _seconds: None,
                clock=lambda: 0.0,
                transport_factory=FakeClient,
                runtime_dir=Path(runtime),
                pid_alive=lambda _pid: False,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "PACKET_NOT_IN_HTTP_PLANE")


if __name__ == "__main__":
    unittest.main()
