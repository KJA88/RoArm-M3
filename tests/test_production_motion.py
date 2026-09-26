import ast
import importlib.util
import json
import math
from pathlib import Path
import requests
import tempfile
import time
import unittest
from unittest.mock import ANY, Mock, patch
from urllib.parse import parse_qs, urlparse

from runtime.core.safety.existing_motions import (
    CANDLE_ARM_TARGETS,
    CANDLE_GRIPPER_EVIDENCE,
    EXISTING_MOTION_INVENTORY,
    OBSERVE_CENTER_ARM_TARGETS,
    OBSERVE_LEFT_ARM_TARGETS,
    OBSERVE_RIGHT_ARM_TARGETS,
    RANDOM_HISTORICAL_TEST_TARGETS,
    READY_ARM_TARGETS,
    READY_TARGETS,
    REFERENCE_DH_TARGETS,
    SCAN_LEFT_BASE_TARGET,
    SCAN_RIGHT_BASE_TARGET,
)
from runtime.core.safety.motion_authority import LocalMotionAuthority
from runtime.core.safety.production_motion import ProductionMotionAdapter
from runtime.core.transport.roarm_http import (
    RoArmHttpError,
    RoArmProductionHttpTransport,
    normalize_feedback,
)


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = (
    ROOT / "milestones/Phase_1_System_Authority/03_deterministic_pipelines"
)


def fresh_state(**changes):
    value = {
        "connected": True,
        "fresh": True,
        "timestamp_unix": time.time(),
        "joints": {
            "base": 0.25,
            "shoulder": 0.0,
            "elbow": 1.0,
            "wrist": 0.0,
            "roll": -0.004601942,
            "gripper": 3.13545673,
        },
    }
    value.update(changes)
    return value


def full_t102(targets):
    joints = dict(fresh_state()["joints"])
    joints.update(targets)
    return {
        "T": 102,
        "base": joints["base"],
        "shoulder": joints["shoulder"],
        "elbow": joints["elbow"],
        "wrist": joints["wrist"],
        "roll": joints["roll"],
        "hand": joints["gripper"],
        "spd": 0,
        "acc": 0,
    }


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.closed = False

    def move_joint(self, joint, target, *, current_joints):
        values = dict(current_joints)
        values[joint] = target
        packet = {
            "T": 102,
            "base": values["base"],
            "shoulder": values["shoulder"],
            "elbow": values["elbow"],
            "wrist": values["wrist"],
            "roll": values["roll"],
            "hand": values["gripper"],
            "spd": 0,
            "acc": 0,
        }
        self.commands.append(packet)
        return {"T": 102}

    def move_arm_pose(self, targets, *, roll, hand):
        packet = {
            "T": 102,
            **targets,
            "roll": roll,
            "hand": hand,
            "spd": 0,
            "acc": 0,
        }
        self.commands.append(packet)
        return {"T": 102}

    def close(self):
        self.closed = True


class ExistingMotionInventoryTests(unittest.TestCase):
    def test_historical_pose_evidence_is_preserved_without_authorization(self):
        self.assertEqual(
            REFERENCE_DH_TARGETS,
            {
                "base": 0.0,
                "shoulder": 1.5,
                "elbow": 0.0,
                "wrist": 0.0,
                "roll": 0.0,
                "hand": 1.0,
            },
        )
        self.assertEqual(
            RANDOM_HISTORICAL_TEST_TARGETS,
            {
                "base": 0.5,
                "shoulder": 1.1,
                "elbow": -0.4,
                "wrist": 0.3,
                "roll": 0.0,
                "hand": 1.0,
            },
        )
        self.assertEqual(
            EXISTING_MOTION_INVENTORY["reference_dh"]["production_status"],
            "BLOCKED",
        )
        self.assertEqual(
            EXISTING_MOTION_INVENTORY["random_historical_test"][
                "production_status"
            ],
            "BLOCKED",
        )

    def test_candle_conflict_remains_unresolved_and_arm_only(self):
        self.assertEqual(CANDLE_GRIPPER_EVIDENCE, (1.49, 1.0))
        self.assertNotIn("hand", CANDLE_ARM_TARGETS)
        candle = EXISTING_MOTION_INVENTORY["candle"]
        self.assertEqual(candle["gripper_resolution"], "UNRESOLVED")
        self.assertEqual(candle["production_status"], "ARM_TARGETS_ONLY")

    def test_ready_strong_evidence_is_preserved_exactly(self):
        self.assertEqual(
            READY_TARGETS,
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
            EXISTING_MOTION_INVENTORY["ready"]["evidence"],
            "physically_used_strong",
        )
        self.assertEqual(
            set(READY_ARM_TARGETS),
            {"base", "shoulder", "elbow", "wrist"},
        )

    def test_observe_arm_only_targets_preserve_roll_and_gripper(self):
        for targets in (
            OBSERVE_LEFT_ARM_TARGETS,
            OBSERVE_CENTER_ARM_TARGETS,
            OBSERVE_RIGHT_ARM_TARGETS,
        ):
            with self.subTest(targets=targets):
                self.assertEqual(
                    set(targets),
                    {"base", "shoulder", "elbow", "wrist"},
                )
                self.assertNotIn("roll", targets)
                self.assertNotIn("hand", targets)


class FakeHttpResponse:
    def __init__(self, packet):
        self.text = json.dumps(packet)

    def raise_for_status(self):
        return None


class FakeHttpSession:
    def __init__(self, error=None):
        self.trust_env = True
        self.error = error
        self.requests = []
        self.closed = False

    def get(self, url, timeout):
        command = json.loads(parse_qs(urlparse(url).query)["json"][0])
        self.requests.append((url, command, timeout))
        if self.error is not None:
            raise self.error
        if command == {"T": 105}:
            return FakeHttpResponse(
                {
                    "T": 1051,
                    "b": 0.25,
                    "s": 0.0,
                    "e": 1.0,
                    "t": 0.0,
                    "r": -0.004601942,
                    "g": 3.13545673,
                }
            )
        return FakeHttpResponse({"T": command["T"]})

    def close(self):
        self.closed = True


class HttpTransportTests(unittest.TestCase):
    def test_fixed_http_state_and_motion_protocol(self):
        http = FakeHttpSession()
        transport = RoArmProductionHttpTransport(session=http)

        feedback = transport.read_state()
        state = normalize_feedback(feedback, base_url=transport.base_url)
        transport.move_joint(
            "base",
            0.25,
            current_joints=state["joints"],
        )
        transport.move_arm_pose(
            {
                "base": 0.0,
                "shoulder": -0.8,
                "elbow": 2.4,
                "wrist": 0.0,
            },
            roll=state["joints"]["roll"],
            hand=state["joints"]["gripper"],
        )
        transport.close()

        self.assertFalse(http.trust_env)
        self.assertEqual(
            [request[1] for request in http.requests],
            [
                {"T": 105},
                {
                    "T": 102,
                    "base": 0.25,
                    "shoulder": 0.0,
                    "elbow": 1.0,
                    "wrist": 0.0,
                    "roll": -0.004601942,
                    "hand": 3.13545673,
                    "spd": 0,
                    "acc": 0,
                },
                {
                    "T": 102,
                    "base": 0.0,
                    "shoulder": -0.8,
                    "elbow": 2.4,
                    "wrist": 0.0,
                    "roll": -0.004601942,
                    "hand": 3.13545673,
                    "spd": 0,
                    "acc": 0,
                },
            ],
        )
        self.assertTrue(
            all(url.startswith("http://192.168.4.1/js?json=")
                for url, _, _ in http.requests)
        )
        self.assertEqual(
            [request[2] for request in http.requests],
            [5.0, 5.0, 5.0],
        )
        self.assertEqual(state["joints"]["base"], 0.25)
        self.assertEqual(state["transport"], "http")
        self.assertTrue(http.closed)

    def test_motion_http_error_is_not_retried(self):
        http = FakeHttpSession(error=requests.Timeout("simulated timeout"))
        transport = RoArmProductionHttpTransport(session=http)

        with self.assertRaises(requests.Timeout):
            transport.move_joint(
                "elbow",
                1.0,
                current_joints=fresh_state()["joints"],
            )

        self.assertEqual(len(http.requests), 1)

    def test_production_transport_has_no_generic_command_api(self):
        public = {
            name
            for name in dir(RoArmProductionHttpTransport)
            if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {"close", "move_arm_pose", "move_joint", "read_state"},
        )

    def test_arm_pose_transport_rejects_non_arm_and_nonfinite_targets(self):
        transport = RoArmProductionHttpTransport(session=FakeHttpSession())
        for targets in (
            {"roll": 0.0},
            {"gripper": 2.0},
            {"hand": 2.0},
            {"unknown": 0.0},
            {"base": math.nan},
            {"base": math.inf},
            {},
        ):
            with self.subTest(targets=targets):
                with self.assertRaises(RoArmHttpError):
                    transport.move_arm_pose(targets, roll=0.0, hand=2.0)
        for roll, hand in ((math.nan, 2.0), (0.0, math.inf)):
            with self.subTest(roll=roll, hand=hand):
                with self.assertRaises(RoArmHttpError):
                    transport.move_arm_pose(
                        READY_ARM_TARGETS,
                        roll=roll,
                        hand=hand,
                    )
        self.assertEqual(transport._session.requests, [])


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
        self.assertEqual(
            transport.commands[0],
            full_t102({"elbow": 1.2}),
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

    def test_uncertain_http_motion_is_not_retried(self):
        transport = Mock()
        transport.move_joint.side_effect = requests.Timeout(
            "simulated motion timeout"
        )
        result = self.adapter(
            fresh_state(), lambda: transport
        ).execute_joint("elbow", 1.0)

        self.assertEqual(result["reason"], "EXECUTION_FAILED")
        self.assertTrue(result["permit_consumed"])
        transport.move_joint.assert_called_once_with(
            "elbow",
            1.0,
            current_joints=ANY,
        )
        transport.close.assert_called_once_with()

    def test_uncertain_combined_pose_is_not_retried(self):
        transport = Mock()
        transport.move_arm_pose.side_effect = requests.Timeout(
            "simulated pose timeout"
        )
        targets = {
            "base": 0.0,
            "shoulder": 0.0,
            "elbow": 1.0,
            "wrist": 0.0,
        }

        result = self.adapter(
            fresh_state(), lambda: transport
        ).execute_named_pose("test_arm_only", targets)

        self.assertEqual(result["reason"], "EXECUTION_FAILED")
        self.assertTrue(result["permits_consumed"])
        transport.move_arm_pose.assert_called_once_with(
            targets,
            roll=-0.004601942,
            hand=3.13545673,
        )
        transport.close.assert_called_once_with()

    def test_invalid_arm_pose_fails_before_transport_opens(self):
        factory = Mock(side_effect=AssertionError("transport must stay closed"))
        result = self.adapter(
            fresh_state(), factory
        ).execute_named_pose(
            "invalid_arm_only",
            {
                "base": 0.0,
                "shoulder": 0.0,
                "elbow": -0.4,
                "wrist": 0.0,
            },
        )

        self.assertEqual(result["reason"], "TARGET_OUT_OF_LIMIT")
        self.assertEqual(result["blocked_joint"], "elbow")
        factory.assert_not_called()

    def test_invalid_pose_preservation_state_fails_before_transport(self):
        valid_joints = fresh_state()["joints"]
        cases = []
        for missing in ("roll", "gripper"):
            joints = dict(valid_joints)
            joints.pop(missing)
            cases.append(joints)
        for field in ("roll", "gripper"):
            joints = dict(valid_joints)
            joints[field] = math.nan
            cases.append(joints)

        for joints in cases:
            with self.subTest(joints=joints):
                factory = Mock(
                    side_effect=AssertionError("transport must stay closed")
                )
                result = self.adapter(
                    fresh_state(joints=joints), factory
                ).execute_named_pose("ready_arm_only", READY_ARM_TARGETS)
                self.assertEqual(
                    result["reason"],
                    "PRESERVATION_STATE_INVALID",
                )
                factory.assert_not_called()

    def test_operational_base_and_verified_joint_are_authorized(self):
        transport = FakeTransport()
        adapter = self.adapter(fresh_state(), lambda: transport)
        self.assertTrue(adapter.execute_joint("elbow", 1.0)["ok"])

        base_transport = FakeTransport()
        result = self.adapter(
            fresh_state(), lambda: base_transport
        ).execute_joint("base", 0.0)
        self.assertTrue(result["ok"])
        self.assertEqual(
            base_transport.commands[0],
            full_t102({"base": 0.0}),
        )

    def test_named_pose_preflights_all_targets_before_execution(self):
        transports = []

        def factory():
            transport = FakeTransport()
            transports.append(transport)
            return transport

        adapter = self.adapter(fresh_state(), factory)
        targets = {
            "base": 0.0,
            "shoulder": 0.0,
            "elbow": 1.0,
            "wrist": 0.0,
        }
        result = adapter.execute_named_pose("mixed", targets)
        self.assertTrue(result["ok"])
        self.assertEqual(len(transports), 1)
        self.assertEqual(
            transports[0].commands,
            [full_t102(targets)],
        )

    def test_ready_and_observe_arm_only_poses_are_authorized(self):
        cases = (
            ("ready_arm_only", READY_ARM_TARGETS),
            ("observe_left_arm_only", OBSERVE_LEFT_ARM_TARGETS),
            ("observe_center_arm_only", OBSERVE_CENTER_ARM_TARGETS),
            ("observe_right_arm_only", OBSERVE_RIGHT_ARM_TARGETS),
        )
        for action, targets in cases:
            with self.subTest(action=action):
                transports = []

                def factory():
                    transport = FakeTransport()
                    transports.append(transport)
                    return transport

                result = self.adapter(
                    fresh_state(), factory
                ).execute_named_pose(action, targets)
                self.assertTrue(result["ok"])
                self.assertTrue(result["permits_consumed"])
                self.assertEqual(len(transports), 1)
                self.assertEqual(
                    transports[0].commands,
                    [full_t102(targets)],
                )

    def test_scan_arm_only_reuses_ready_then_exact_base_endpoint(self):
        for action, endpoint in (
            ("scan_left_arm_only", SCAN_LEFT_BASE_TARGET),
            ("scan_right_arm_only", SCAN_RIGHT_BASE_TARGET),
        ):
            with self.subTest(action=action):
                transports = []

                def factory():
                    transport = FakeTransport()
                    transports.append(transport)
                    return transport

                result = self.adapter(
                    fresh_state(), factory
                ).execute_named_sequence(
                    action,
                    (
                        ("ready_arm_only", READY_ARM_TARGETS),
                        ("scan_endpoint", endpoint),
                    ),
                )
                self.assertTrue(result["ok"])
                self.assertEqual(len(transports), 2)
                self.assertEqual(
                    transports[0].commands,
                    [full_t102(READY_ARM_TARGETS)],
                )
                self.assertEqual(
                    transports[-1].commands[0],
                    full_t102(endpoint),
                )

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
            (
                "milestone_03_ready_motion_authority.py",
                "execute_ready",
                "ready_arm_only",
                READY_ARM_TARGETS,
            ),
            (
                "milestone_03_observe_left_motion_authority.py",
                "execute_observe_left",
                "observe_left_arm_only",
                OBSERVE_LEFT_ARM_TARGETS,
            ),
            (
                "milestone_03_observe_center_motion_authority.py",
                "execute_observe_center",
                "observe_center_arm_only",
                OBSERVE_CENTER_ARM_TARGETS,
            ),
            (
                "milestone_03_observe_right_motion_authority.py",
                "execute_observe_right",
                "observe_right_arm_only",
                OBSERVE_RIGHT_ARM_TARGETS,
            ),
        ]
        for filename, function_name, action, targets in cases:
            with self.subTest(filename=filename):
                module = self.load_wrapper(filename)
                module.execute_named_pose = Mock(return_value={"ok": False})
                getattr(module, function_name)()
                module.execute_named_pose.assert_called_once_with(
                    action, targets
                )

        for filename, function_name, action, endpoint in (
            (
                "milestone_03_scan_left_motion_authority.py",
                "execute_scan_left",
                "scan_left_arm_only",
                SCAN_LEFT_BASE_TARGET,
            ),
            (
                "milestone_03_scan_right_motion_authority.py",
                "execute_scan_right",
                "scan_right_arm_only",
                SCAN_RIGHT_BASE_TARGET,
            ),
        ):
            with self.subTest(filename=filename):
                module = self.load_wrapper(filename)
                module.execute_named_sequence = Mock(
                    return_value={"ok": False}
                )
                getattr(module, function_name)()
                module.execute_named_sequence.assert_called_once_with(
                    action,
                    (
                        ("ready_arm_only", READY_ARM_TARGETS),
                        (
                            "scan_left" if "left" in action else "scan_right",
                            endpoint,
                        ),
                    ),
                )

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
    def test_production_transport_and_state_reader_have_no_serial_fallback(self):
        paths = (
            ROOT / "runtime/core/safety/production_motion.py",
            ROOT / "runtime/core/supervisor/mechanical_supervisor.py",
            MILESTONE / "milestone_03_state_reader.py",
        )
        for path in paths:
            with self.subTest(path=path):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = {
                    name.split(".")[0]
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.Import, ast.ImportFrom))
                    for name in (
                        [item.name for item in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
                }
                self.assertNotIn("serial", imports)

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
