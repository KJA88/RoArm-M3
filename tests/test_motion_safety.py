import ast
import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from runtime.core.safety import (
    LocalMotionAuthority,
    MotionNotAuthorized,
    evaluate_motion_permit,
)
from runtime.core.supervisor import mechanical_supervisor


NOW = 1_800_000_000.0
DEFAULT_STATE = object()
LIMITS = {
    "shoulder": (-1.3, 1.1),
    "elbow": (-0.366, 2.734),
    "wrist": (-1.0, 1.4),
}


def state(timestamp=NOW, **changes):
    value = {
        "connected": True,
        "fresh": True,
        "timestamp_unix": timestamp,
        "joints": {"shoulder": 0.0, "elbow": 1.0, "wrist": 0.0},
    }
    value.update(changes)
    return value


def evaluate(joint="shoulder", target=0.0, current=DEFAULT_STATE, **kwargs):
    extra = kwargs.pop("target_extra", {})
    return evaluate_motion_permit(
        current_state=state() if current is DEFAULT_STATE else current,
        target={"joint": joint, "target": target, **extra},
        now=kwargs.pop("now", NOW),
        **kwargs,
    )


class PermitDecisionTests(unittest.TestCase):
    def test_state_failures(self):
        cases = [
            (None, "STATE_MISSING"),
            (state(connected=False), "STATE_DISCONNECTED"),
            (state(fresh=False), "STATE_NOT_FRESH"),
            (state(timestamp="bad"), "STATE_TIMESTAMP_INVALID"),
            (state(NOW - 2.01), "STATE_STALE"),
        ]
        for current, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(evaluate(current=current)["reason"], reason)

    def test_verified_limits_are_inclusive(self):
        for joint, (minimum, maximum) in LIMITS.items():
            for target in (minimum, (minimum + maximum) / 2, maximum):
                with self.subTest(joint=joint, target=target):
                    self.assertTrue(evaluate(joint, target)["allowed"])
            for target in (
                math.nextafter(minimum, -math.inf),
                math.nextafter(maximum, math.inf),
            ):
                with self.subTest(joint=joint, target=target):
                    self.assertEqual(
                        evaluate(joint, target)["reason"],
                        "TARGET_OUT_OF_LIMIT",
                    )

    def test_base_verified_operational_bounds_are_inclusive(self):
        minimum = -1.578466231
        maximum = 1.610679827
        for target in (minimum, maximum):
            with self.subTest(target=target):
                result = evaluate("base", target)
                self.assertTrue(result["allowed"])
                self.assertEqual(
                    result["checks"]["verified_operational_bounds"]["kind"],
                    "operational_not_mechanical",
                )
        for target in (
            math.nextafter(minimum, -math.inf),
            math.nextafter(maximum, math.inf),
        ):
            with self.subTest(target=target):
                self.assertEqual(
                    evaluate("base", target)["reason"],
                    "TARGET_OUT_OF_LIMIT",
                )

    def test_unverified_unknown_and_nonfinite_targets_deny(self):
        for joint in ("roll", "gripper"):
            self.assertEqual(evaluate(joint, 0.0)["reason"], "LIMIT_UNVERIFIED")
        self.assertEqual(evaluate("unknown", 0.0)["reason"], "UNKNOWN_JOINT")
        for target in (math.nan, math.inf, -math.inf):
            self.assertEqual(
                evaluate("shoulder", target)["reason"], "TARGET_INVALID"
            )
        self.assertTrue(evaluate("elbow", 1.0)["allowed"])

    def test_unreadable_limits_deny(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "limits.json"
            self.assertEqual(
                evaluate(limits_path=path)["reason"], "LIMITS_UNREADABLE"
            )
            path.write_text("{", encoding="utf-8")
            self.assertEqual(
                evaluate(limits_path=path)["reason"], "LIMITS_UNREADABLE"
            )

    def test_only_relevant_local_evidence_participates(self):
        guardian = {"status": "red", "cameras": "red", "ui": "unknown"}
        result = evaluate("elbow", 1.0, guardian_state=guardian)
        self.assertTrue(result["allowed"])
        self.assertFalse(result["checks"]["guardian_required"])

        current = state(joints={"shoulder": 0.0})
        self.assertTrue(evaluate(
            "shoulder", 0.2, current=current,
            target_extra={"max_delta": 0.25},
        )["allowed"])
        self.assertEqual(evaluate(
            "shoulder", 0.3, current=current,
            target_extra={"max_delta": 0.25},
        )["reason"], "MAX_DELTA_EXCEEDED")


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit_path = Path(self.temp.name) / "motion_audit.jsonl"

    def authority(self, ttl=5.0):
        return LocalMotionAuthority(
            audit_path=self.audit_path,
            permit_ttl_s=ttl,
        )

    def issue(self, authority, joint="shoulder", target=0.5):
        return authority.issue_permit(
            current_state=state(),
            joint=joint,
            target=target,
            now=NOW,
        )

    def authorize(self, authority, permit, joint="shoulder", target=0.5, now=NOW + 1):
        return authority.authorize_once(
            permit=permit,
            action="move_joint",
            joint=joint,
            target=target,
            current_state=state(now),
            now=now,
        )

    def test_permit_is_short_lived_and_single_use(self):
        authority = self.authority()
        permit = self.issue(authority)
        self.assertTrue(self.authorize(authority, permit)["allowed"])
        self.assertTrue(permit.consumed)
        self.assertEqual(
            self.authorize(authority, permit)["reason"], "PERMIT_CONSUMED"
        )

        authority = self.authority(ttl=2)
        permit = self.issue(authority)
        self.assertEqual(
            self.authorize(authority, permit, now=NOW + 2)["reason"],
            "PERMIT_EXPIRED",
        )
        self.assertFalse(permit.consumed)

    def test_permit_matches_exact_request_and_local_issuer(self):
        for joint, target in (("elbow", 0.5), ("shoulder", 0.6)):
            authority = self.authority()
            permit = self.issue(authority)
            result = self.authorize(authority, permit, joint, target)
            self.assertEqual(result["reason"], "PERMIT_MISMATCH")
            self.assertFalse(permit.consumed)

        issuer, other = self.authority(), self.authority()
        permit = self.issue(issuer)
        self.assertEqual(
            self.authorize(other, permit)["reason"],
            "PERMIT_ISSUER_INVALID",
        )

    def test_combined_permits_are_consumed_atomically(self):
        authority = self.authority()
        shoulder = self.issue(authority, "shoulder", 0.5)
        elbow = self.issue(authority, "elbow", 1.0)
        requests = [
            {
                "permit": shoulder,
                "action": "move_joint",
                "joint": "shoulder",
                "target": 0.5,
            },
            {
                "permit": elbow,
                "action": "move_joint",
                "joint": "elbow",
                "target": 1.1,
            },
        ]

        denied = authority.authorize_many_once(
            requests=requests,
            current_state=state(NOW + 1),
            now=NOW + 1,
        )
        self.assertEqual(denied["reason"], "PERMIT_MISMATCH")
        self.assertFalse(shoulder.consumed)
        self.assertFalse(elbow.consumed)

        requests[1]["target"] = 1.0
        allowed = authority.authorize_many_once(
            requests=requests,
            current_state=state(NOW + 1),
            now=NOW + 1,
        )
        self.assertTrue(allowed["allowed"])
        self.assertTrue(shoulder.consumed)
        self.assertTrue(elbow.consumed)

    def test_audit_covers_the_authorization_lifecycle(self):
        authority = self.authority()
        permit = self.issue(authority)
        self.authorize(authority, permit)
        self.authorize(authority, permit)
        authority.record_move_start(permit)
        authority.record_move_result(permit, succeeded=True)
        events = [
            json.loads(line)["event"]
            for line in self.audit_path.read_text(encoding="utf-8").splitlines()
        ]
        for event in (
            "permit_issued", "move_requested", "permit_accepted",
            "permit_rejected", "move_start", "move_success", "permit_consumed",
        ):
            self.assertIn(event, events)


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.closed = False

    def move_joint(self, joint, target):
        packet = {"T": 102, joint: target, "spd": 0, "acc": 0}
        self.commands.append(packet)
        return {"T": 102}

    def move_arm_pose(self, targets):
        packet = {"T": 102, **targets, "spd": 0, "acc": 0}
        self.commands.append(packet)
        return {"T": 102}

    def close(self):
        self.closed = True


class SupervisorTests(unittest.TestCase):
    def test_import_and_constructor_are_inert(self):
        transport = FakeTransport()
        importlib.reload(mechanical_supervisor)
        supervisor = mechanical_supervisor.MechanicalSupervisor(transport=transport)
        self.assertEqual(transport.commands, [])
        supervisor.close()
        self.assertTrue(transport.closed)

    def test_pose_cannot_bypass_single_joint_permit(self):
        with tempfile.TemporaryDirectory() as directory:
            authority = LocalMotionAuthority(
                audit_path=Path(directory) / "audit.jsonl"
            )
            permit = authority.issue_permit(
                current_state=state(), joint="shoulder", target=0.5, now=NOW
            )
            transport = FakeTransport()
            supervisor = mechanical_supervisor.MechanicalSupervisor(
                transport=transport, authority=authority
            )
            with self.assertRaises(MotionNotAuthorized):
                supervisor.move_to_pose(
                    250, 0, 300, -1.0,
                    permit=permit, current_state=state(NOW + 1), now=NOW + 1,
                )
            self.assertEqual(transport.commands, [])
            self.assertFalse(permit.consumed)

    def test_arm_pose_consumes_permits_and_sends_one_combined_command(self):
        with tempfile.TemporaryDirectory() as directory:
            authority = LocalMotionAuthority(
                audit_path=Path(directory) / "audit.jsonl"
            )
            targets = {"base": 0.0, "shoulder": 0.5}
            permits = {
                joint: authority.issue_permit(
                    current_state=state(),
                    joint=joint,
                    target=target,
                    now=NOW,
                )
                for joint, target in targets.items()
            }
            transport = FakeTransport()
            supervisor = mechanical_supervisor.MechanicalSupervisor(
                transport=transport,
                authority=authority,
            )

            supervisor.move_arm_pose(
                targets,
                permits=permits,
                current_state=state(NOW + 1),
                now=NOW + 1,
            )

            self.assertEqual(
                transport.commands,
                [
                    {
                        "T": 102,
                        "base": 0.0,
                        "shoulder": 0.5,
                        "spd": 0,
                        "acc": 0,
                    }
                ],
            )
            self.assertTrue(all(permit.consumed for permit in permits.values()))

    def test_no_generic_command_api_or_automatic_setup_commands(self):
        supervisor = mechanical_supervisor.MechanicalSupervisor
        self.assertTrue(hasattr(supervisor, "move_joint"))
        self.assertFalse(hasattr(supervisor, "send_command"))
        self.assertFalse(hasattr(supervisor, "_write_raw"))
        source = Path(mechanical_supervisor.__file__).read_text(encoding="utf-8")
        for forbidden in ('"T": 210', '"T": 111', "serial.Serial"):
            self.assertNotIn(forbidden, source)

    def test_permit_decision_module_has_no_transport_calls(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "runtime/core/safety/motion_permit.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_modules = {"serial", "socket", "urllib", "requests"}
        forbidden_calls = {"send", "sendall", "urlopen", "write"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(
                    forbidden_modules
                    & {item.name.split(".")[0] for item in node.names}
                )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(
                    (node.module or "").split(".")[0], forbidden_modules
                )
            elif isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", None))
                self.assertNotIn(name, forbidden_calls)


if __name__ == "__main__":
    unittest.main()
