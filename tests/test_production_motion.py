import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from runtime.core.safety.motion_authority import LocalMotionAuthority
from runtime.core.safety.production_motion import ProductionMotionAdapter


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = (
    ROOT / "milestones/Phase_1_System_Authority/03_deterministic_pipelines"
)


def fresh_state(**changes):
    value = {
        "connected": True,
        "fresh": True,
        "timestamp_unix": time.time(),
        "joints": {"shoulder": 0.0, "elbow": 1.0, "wrist": 0.0},
    }
    value.update(changes)
    return value


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.closed = False

    def write(self, payload):
        self.commands.append(payload)

    def readline(self):
        return b'{"T":1051}\n'

    def close(self):
        self.closed = True


class ProductionAdapterTests(unittest.TestCase):
    def adapter(self, state, transport_factory):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        authority = LocalMotionAuthority(
            audit_path=Path(self.temp.name) / "audit.jsonl"
        )
        return ProductionMotionAdapter(
            state_reader=lambda: state,
            transport_factory=transport_factory,
            authority=authority,
        )

    def test_authorized_joint_uses_supervisor_and_consumes_permit(self):
        transport = FakeTransport()
        adapter = self.adapter(fresh_state(), lambda: transport)
        result = adapter.execute_joint("elbow", 1.2)

        self.assertTrue(result["ok"])
        self.assertTrue(result["permit_consumed"])
        self.assertTrue(transport.closed)
        self.assertEqual(len(transport.commands), 1)
        packet = json.loads(transport.commands[0])
        self.assertEqual(
            packet,
            {"T": 102, "elbow": 1.2, "spd": 0, "acc": 0},
        )

    def test_invalid_or_stale_state_never_opens_transport(self):
        factory = Mock(side_effect=AssertionError("transport must stay closed"))
        for state, reason in (
            (None, "STATE_MISSING"),
            (fresh_state(fresh=False), "STATE_NOT_FRESH"),
            (
                fresh_state(timestamp_unix=time.time() - 10),
                "STATE_STALE",
            ),
        ):
            with self.subTest(reason=reason):
                result = self.adapter(state, factory).execute_joint(
                    "shoulder", 0.0
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["reason"], reason)
        factory.assert_not_called()

    def test_unverified_joint_does_not_block_verified_joint(self):
        transport = FakeTransport()
        adapter = self.adapter(fresh_state(), lambda: transport)
        self.assertTrue(adapter.execute_joint("elbow", 1.0)["ok"])

        blocked_factory = Mock()
        blocked = self.adapter(fresh_state(), blocked_factory).execute_joint(
            "base", 0.0
        )
        self.assertEqual(blocked["reason"], "LIMIT_UNVERIFIED")
        blocked_factory.assert_not_called()

    def test_named_pose_preflights_all_targets_before_execution(self):
        factory = Mock()
        adapter = self.adapter(fresh_state(), factory)
        result = adapter.execute_named_pose(
            "mixed", {"shoulder": 0.0, "base": 0.0}
        )
        self.assertEqual(result["reason"], "LIMIT_UNVERIFIED")
        self.assertEqual(result["blocked_joint"], "base")
        factory.assert_not_called()

    def test_gripper_map_is_reported_but_not_activated(self):
        result = self.adapter(fresh_state(), Mock()).gripper_finding("open")
        self.assertEqual(result["reason"], "GRIPPER_POLICY_REVIEW_REQUIRED")
        self.assertTrue(result["calibration_human_verified"])
        self.assertEqual(result["calibration"]["safe_min"], 1.6)
        self.assertEqual(result["calibration"]["safe_max"], 2.8)


class DelegationTests(unittest.TestCase):
    def load_wrapper(self, filename):
        return load_file(
            "test_" + filename.removesuffix(".py"),
            MILESTONE / filename,
        )

    def test_joint_wrapper_delegates(self):
        module = self.load_wrapper(
            "milestone_03_joint_motion_authority.py"
        )
        module.execute_joint = Mock(return_value={"ok": True})
        self.assertEqual(
            module.execute_constrained_joint_move("elbow", 1.0),
            {"ok": True},
        )
        module.execute_joint.assert_called_once_with("elbow", 1.0)

    def test_named_compatibility_wrappers_delegate(self):
        cases = [
            ("milestone_03_ready_motion_authority.py", "execute_ready"),
            (
                "milestone_03_observe_left_motion_authority.py",
                "execute_observe_left",
            ),
            (
                "milestone_03_observe_center_motion_authority.py",
                "execute_observe_center",
            ),
            (
                "milestone_03_observe_right_motion_authority.py",
                "execute_observe_right",
            ),
        ]
        for filename, function_name in cases:
            with self.subTest(filename=filename):
                module = self.load_wrapper(filename)
                module.execute_named_pose = Mock(return_value={"ok": False})
                getattr(module, function_name)()
                module.execute_named_pose.assert_called_once()

        for filename, function_name in (
            ("milestone_03_scan_left_motion_authority.py", "execute_scan_left"),
            (
                "milestone_03_scan_right_motion_authority.py",
                "execute_scan_right",
            ),
        ):
            with self.subTest(filename=filename):
                module = self.load_wrapper(filename)
                module.execute_named_sequence = Mock(
                    return_value={"ok": False}
                )
                getattr(module, function_name)()
                module.execute_named_sequence.assert_called_once()

    def test_special_compatibility_wrappers_delegate(self):
        motion = self.load_wrapper("milestone_03_motion_authority.py")
        motion.execute_named_pose = Mock(return_value={"ok": False})
        motion.deny_unsupported = Mock(return_value={"ok": False})
        motion.execute_candle()
        motion.execute_lissajous()
        motion.execute_named_pose.assert_called_once()
        motion.deny_unsupported.assert_called_once()

        home = self.load_wrapper("milestone_03_home_motion_authority.py")
        home.deny_unsupported = Mock(return_value={"ok": False})
        home.execute_home()
        home.deny_unsupported.assert_called_once()

        gripper = self.load_wrapper(
            "milestone_03_gripper_motion_authority.py"
        )
        gripper.inspect_gripper = Mock(return_value={"ok": False})
        gripper.execute_gripper_position("open")
        gripper.inspect_gripper.assert_called_once_with("open")

    def test_daily_cli_delegates(self):
        module = load_file(
            "test_roarm_simple_move",
            ROOT / "scripts/roarm_simple_move.py",
        )
        module.execute_joint = Mock(return_value={"ok": True})
        module.deny_unsupported = Mock(return_value={"ok": False})
        module.request_joint("wrist", 0.2)
        module.request_xyz(1, 2, 3)
        module.execute_joint.assert_called_once_with("wrist", 0.2)
        module.deny_unsupported.assert_called_once()

    def test_verified_named_pose_values_are_preserved(self):
        expected = {
            "milestone_03_ready_motion_authority.py": (
                "READY_TARGETS",
                (0.001533981, -0.832951568, 2.399145952, 0.004601942, 0.0, 3.163068385),
            ),
            "milestone_03_observe_left_motion_authority.py": (
                "TARGETS",
                (1.610679827, -0.832951568, 2.411417799, 0.006135923, 0.0, 3.152330519),
            ),
            "milestone_03_observe_center_motion_authority.py": (
                "TARGETS",
                (-0.030679616, -0.832951568, 2.460505184, 0.004601942, 0.001533981, 3.146194596),
            ),
            "milestone_03_observe_right_motion_authority.py": (
                "TARGETS",
                (-1.578466231, -0.832951568, 2.458971203, 0.001533981, 0.010737866, 3.143126634),
            ),
        }
        keys = ("base", "shoulder", "elbow", "wrist", "roll", "hand")
        for filename, (attribute, values) in expected.items():
            with self.subTest(filename=filename):
                module = self.load_wrapper(filename)
                self.assertEqual(
                    getattr(module, attribute),
                    dict(zip(keys, values)),
                )

        for side, base in (("left", 1.610679827), ("right", -1.578466231)):
            module = self.load_wrapper(
                f"milestone_03_scan_{side}_motion_authority.py"
            )
            self.assertEqual(
                module.READY_TARGETS,
                {
                    "base": 0.001533981,
                    "shoulder": -0.832951568,
                    "elbow": 2.399145952,
                    "wrist": 0.004601942,
                    "roll": 0.0,
                    "hand": 3.163068385,
                },
            )
            self.assertEqual(
                getattr(module, f"{side.upper()}_BASE_TARGET"),
                {"base": base},
            )


class StaticProductionPathTests(unittest.TestCase):
    def test_mcp_has_no_direct_transport_or_raw_motion_packets(self):
        path = ROOT / "mcp/mcp_server.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_imports = {"serial", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(
                    forbidden_imports
                    & {alias.name.split(".")[0] for alias in node.names}
                )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(
                    (node.module or "").split(".")[0], forbidden_imports
                )
            elif isinstance(node, ast.Call):
                self.assertNotEqual(getattr(node.func, "attr", None), "write")
            elif isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant):
                        self.assertNotEqual(key.value, "T")

    def test_in_scope_wrappers_have_no_transport_or_raw_packets(self):
        paths = list(MILESTONE.glob("milestone_03_*motion_authority.py"))
        paths.append(ROOT / "scripts/roarm_simple_move.py")
        for path in paths:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        names = (
                            [item.name for item in node.names]
                            if isinstance(node, ast.Import)
                            else [node.module or ""]
                        )
                        self.assertNotIn(
                            "serial", {name.split(".")[0] for name in names}
                        )
                    elif isinstance(node, ast.Call):
                        self.assertNotEqual(
                            getattr(node.func, "attr", None), "write"
                        )

    def test_only_one_motion_permit_implementation_exists(self):
        definitions = []
        for path in (ROOT / "runtime").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "MotionPermit":
                    definitions.append(path)
        self.assertEqual(
            definitions,
            [ROOT / "runtime/core/safety/motion_permit.py"],
        )

    def test_mcp_joint_tool_reaches_compatibility_wrapper(self):
        tree = ast.parse(
            (ROOT / "mcp/mcp_server.py").read_text(encoding="utf-8")
        )
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "move_constrained_joint"
        )
        calls = {
            getattr(node.func, "id", None)
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
        }
        self.assertIn("execute_constrained_joint_move", calls)


if __name__ == "__main__":
    unittest.main()
