"""Pi-hosted commands for the allowlisted poses and patterns.

Windows may call `roarm list` locally. `roarm run` and `roarm stop`
copy this tree to the Pi. Discrete poses use HTTP after the route
gate and a fresh T105. Lissajous, circle, and spiral read their
existing points and send numbered T1041 datagrams from 192.168.4.2.
Those lesson scripts are not executed, and there is no serial path.
Torque, start and return poses, and T105 stay on HTTP. `stop` ends
further points and leaves torque enabled.
"""
import ast
import io
import json
import os
import random
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from runtime.core.safety.pattern_registry import (
    PATTERN_ROOT,
    REGISTRY,
    command_inventory,
    load_steps,
)
from runtime.core.safety.production_motion import ProductionMotionAdapter


RUNTIME_DIR = Path("/home/KA_PI/syzygy-runtime/roarm")
LOCAL_EXECUTION_ENV = "ROARM_PATTERN_EXECUTE_LOCAL"
REMOTE_TREE = "~/roarm-m3-pattern-cmd"
_ENTRY = "runtime/core/safety/pattern_command_pi_entry.py"
_RUN_TIMEOUT_S = 900
_ARM_T = {100, 101, 102, 104, 1041, 210}
_ALLOWED_T = _ARM_T | {105}
TRAJECTORY_UDP_PORT = 4210
TRAJECTORY_UDP_MAX_BYTES = 384
TRAJECTORY_PI_IP = "192.168.4.2"
TRAJECTORY_ARM_IP = "192.168.4.1"
TRAJECTORY_RELEASE_WAIT_S = 0.15
PREFLIGHT_ATTEMPTS = 5
PREFLIGHT_GAP_S = 1.0
_BASE_KEY = "b"
CONTINUOUS_PATTERNS = ("lissajous", "circle", "spiral")
SSH_HOST_ENV = "ROARM_CENTER_IK_SSH_HOST"
DEFAULT_SSH_HOST = "raspi"
REQUIRED_DEVICE = "wlan0"
_SKIP_DIR_NAMES = {".git", "__pycache__", ".venv", "venv"}

_pattern_pi_entry_depth = 0


class PatternClosed(Exception):
    """Stop the session. No further HTTP request is made."""


@contextmanager
def pattern_pi_entry_scope():
    global _pattern_pi_entry_depth
    _pattern_pi_entry_depth += 1
    try:
        yield
    finally:
        _pattern_pi_entry_depth -= 1


def _repository_root():
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        marker = candidate / "runtime" / "core" / "safety" / "production_motion.py"
        if marker.is_file():
            return candidate
    raise RuntimeError("repository root not found")


def ssh_host():
    host = os.environ.get(SSH_HOST_ENV, DEFAULT_SSH_HOST)
    if not host or any(character.isspace() for character in host):
        raise RuntimeError("RoArm pattern SSH host is not a single token")
    if host.startswith("-"):
        raise RuntimeError("RoArm pattern SSH host is not a hostname")
    return host


def build_tree_archive(root=None):
    """Gzip the working tree that the Pi process must execute."""
    root = _repository_root() if root is None else Path(root)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in _SKIP_DIR_NAMES for part in relative.parts):
                continue
            if path.suffix == ".pyc":
                continue
            archive.add(path, arcname=relative.as_posix())
    return buffer.getvalue()


def _default_runner(args, input_bytes=None, timeout_s=180):
    return subprocess.run(
        args,
        input=input_bytes,
        capture_output=True,
        timeout=timeout_s,
    )


def parse_ip_route_get(text):
    """Return the device and source from `ip route get` output."""
    device = None
    source = None
    tokens = str(text).split()
    for index, token in enumerate(tokens[:-1]):
        if token == "dev":
            device = tokens[index + 1]
        elif token == "src":
            source = tokens[index + 1]
    return device, source


def evaluate_arm_route(text):
    """Refuse unless 192.168.4.1 is on wlan0 from 192.168.4.2.

    A passing result is None. Any other route sends no arm packet.
    """
    device, source = parse_ip_route_get(text)
    if device != REQUIRED_DEVICE:
        return _route_refusal("ARM_ROUTE_WRONG_INTERFACE", text, device, source)
    if source != TRAJECTORY_PI_IP:
        return _route_refusal("ARM_ROUTE_WRONG_SOURCE", text, device, source)
    return None


def _route_refusal(reason, text, device, source):
    return {
        "reason": reason,
        "arm_route": {
            "destination": TRAJECTORY_ARM_IP,
            "device": device,
            "source": source,
            "required_device": REQUIRED_DEVICE,
            "required_source": TRAJECTORY_PI_IP,
            "text": " ".join(str(text).split()),
        },
    }


def read_arm_route():
    """Ask the local kernel how it would reach the arm. No RoArm request."""
    try:
        completed = subprocess.run(
            ["ip", "-4", "route", "get", TRAJECTORY_ARM_IP],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    if completed.returncode != 0:
        return completed.stderr or completed.stdout or "ip route get failed"
    return completed.stdout


def _fresh_t105_preflight(adapter):
    """Up to five single T105 reads. Stop on the first fresh state."""
    last_denied = None
    for attempt in range(1, PREFLIGHT_ATTEMPTS + 1):
        if attempt > 1:
            try:
                adapter.sleep_fn(PREFLIGHT_GAP_S)
            except Exception as exc:
                return (
                    None,
                    {"reason": "PREFLIGHT_WAIT_FAILED", "error": str(exc)},
                    attempt - 1,
                )
        state, denied = adapter._state("pattern_run")
        if denied is None:
            return state, None, attempt
        last_denied = denied
    return None, last_denied, PREFLIGHT_ATTEMPTS


def _refused(reason, **details):
    return {
        "ok": False,
        "authorized": False,
        "command": details.pop("command", None),
        "pattern": details.pop("pattern", None),
        "reason": reason,
        "hardware_action": "NONE",
        "position_verified": False,
        "settled_claim": False,
        "packets_sent": 0,
        "motion_packets_sent": 0,
        **details,
    }


def _parse(argv):
    if list(argv) == ["list"]:
        return ("list", None)
    if list(argv) == ["stop"]:
        return ("stop", None)
    if list(argv) == ["torque-off"]:
        return ("torque-off", None)
    if len(argv) == 2 and argv[0] == "run" and argv[1] in REGISTRY:
        return ("run", argv[1])
    return None


def format_inventory():
    lines = ["name\tkind\tsource"]
    for item in command_inventory():
        lines.append(f"{item['name']}\t{item['kind']}\t{item['source']}")
    return "\n".join(lines)


def pattern_transport(name):
    """UDP for the three lesson curves. HTTP for every other command."""
    if name in CONTINUOUS_PATTERNS:
        return "udp"
    return "http"


def trajectory_udp_address():
    """Arm AP address. The port matches trajectory_udp.h."""
    raw = os.environ.get("ROARM_HTTP_BASE_URL", "http://192.168.4.1")
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    host = parsed.hostname or "192.168.4.1"
    return host, TRAJECTORY_UDP_PORT


def _new_stream_id():
    return random.SystemRandom().randrange(1, 0x100000000)


def trajectory_datagram(packet, sid, seq):
    """Envelope around one unchanged T1041 object. No newline, no replay copy."""
    if not isinstance(packet, dict) or packet.get("T") != 1041:
        raise ValueError("trajectory datagram requires T1041")
    if isinstance(sid, bool) or not isinstance(sid, int) or not 1 <= sid <= 0xFFFFFFFF:
        raise ValueError("trajectory stream id is invalid")
    if isinstance(seq, bool) or not isinstance(seq, int) or not 0 <= seq <= 0xFFFFFFFF:
        raise ValueError("trajectory sequence is invalid")
    payload = json.dumps(
        {"sid": sid, "seq": seq, "cmd": packet},
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > TRAJECTORY_UDP_MAX_BYTES:
        raise ValueError("trajectory datagram exceeds 384 bytes")
    return payload


def _default_udp_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _assigned_constant(tree, name):
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)
    raise ValueError(f"missing {name}")


def _call_named(node, owner, method):
    func = getattr(node, "func", None)
    return (
        isinstance(node, ast.Call)
        and isinstance(func, ast.Attribute)
        and func.attr == method
        and isinstance(func.value, ast.Name)
        and func.value.id == owner
    )


def _statements(node):
    body = getattr(node, "body", None)
    if not isinstance(body, list):
        return
    for stmt in body:
        yield stmt
        yield from _statements(stmt)
        for extra in ("orelse", "finalbody"):
            block = getattr(stmt, extra, None)
            if isinstance(block, list):
                for item in block:
                    yield item
                    yield from _statements(item)


def _statement_call(stmt):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value
    if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
        return stmt.value
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.value, ast.Call):
        return stmt.value
    return None


def _open_timing(function):
    """Timeout and the sleep that follows serial.Serial in one function."""
    timeout_s = None
    settle_s = None
    for stmt in _statements(function):
        call = _statement_call(stmt)
        if call is None:
            continue
        if timeout_s is None and _call_named(call, "serial", "Serial"):
            for keyword in call.keywords:
                if keyword.arg == "timeout" and isinstance(
                    keyword.value, ast.Constant
                ):
                    timeout_s = keyword.value.value
        elif timeout_s is not None and settle_s is None and _call_named(
            call, "time", "sleep"
        ):
            if call.args and isinstance(call.args[0], ast.Constant):
                settle_s = call.args[0].value
                break
    if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool):
        raise ValueError("serial timeout missing")
    if not isinstance(settle_s, (int, float)) or isinstance(settle_s, bool):
        raise ValueError("serial settle missing")
    return float(timeout_s), float(settle_s)


def lesson_serial_profile(root, name):
    """Port, baud, timeout, and settle sleep from the lesson script."""
    path = Path(root) / REGISTRY[name]["source"]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    port = _assigned_constant(tree, "PORT")
    baud = _assigned_constant(tree, "BAUD")
    if not isinstance(port, str) or not port:
        raise ValueError("serial port missing")
    if isinstance(baud, bool) or not isinstance(baud, int):
        raise ValueError("serial baud missing")
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    opener = functions.get("open_serial") or functions.get("main")
    if opener is None:
        raise ValueError("serial open missing")
    timeout_s, settle_s = _open_timing(opener)
    return {
        "port": port,
        "baud": baud,
        "timeout_s": timeout_s,
        "settle_s": settle_s,
    }


class TrajectoryUdpLink:
    """One datagram per T1041 point. No receive and no replay."""

    def __init__(self, address, socket_factory, stream_id_factory=None):
        self.address = address
        self.socket_factory = socket_factory
        self.stream_id_factory = stream_id_factory or _new_stream_id
        self.sock = None
        self.opened = False
        self.sid = None

    def open(self):
        if self.sock is not None:
            return
        sock = self.socket_factory()
        sock.setblocking(False)
        sock.bind((TRAJECTORY_PI_IP, 0))
        sock.connect(self.address)
        self.sock = sock
        self.opened = True

    def allocate_sid(self):
        sid = int(self.stream_id_factory())
        if isinstance(sid, bool) or not isinstance(sid, int) or not 1 <= sid <= 0xFFFFFFFF:
            raise ValueError("trajectory stream id is invalid")
        self.sid = sid
        return sid

    def send_point(self, packet, sid, seq):
        payload = trajectory_datagram(packet, sid, seq)
        sent = self.sock.send(payload)
        if sent != len(payload):
            raise OSError("short trajectory datagram")

    def close(self):
        sock = self.sock
        self.sock = None
        close = getattr(sock, "close", None)
        if close is not None:
            close()


def _write_json_atomic(path, payload):
    """Replace the status file only after a flushed, durable temp write."""
    directory = Path(path).parent
    fd, temporary = tempfile.mkstemp(prefix=".transport-status-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class PatternHttpSession:
    """HTTP for discrete poses. UDP for a continuous pattern."""

    def __init__(self, client, stop_path, sleep_fn, clock, udp_link=None, pattern_name=None):
        self.client = client
        self.stop_path = Path(stop_path)
        self.sleep_fn = sleep_fn
        self.clock = clock
        self.udp_link = udp_link
        self.pattern_name = pattern_name
        self.sent = []
        self.arm_packets = 0
        self.error = None
        self.error_detail = None
        self.stopped = False

    def _stopped(self):
        return self.stop_path.is_file()

    def execute(self, steps):
        self._publish_transport(
            transport_state="idle",
            active=False,
            last_sequence=None,
            active_failure=None,
            failure_detail=None,
        )
        try:
            if self.udp_link is not None:
                self._execute_udp(steps)
                return
            self._execute_http(steps)
        finally:
            self._publish_transport(transport_state="idle", active=False)

    def _status_path(self):
        return Path(self.stop_path).parent / "transport-status.json"

    def _publish_transport(self, **fields):
        """Record link facts for Guardian. This is not on the UDP point loop."""
        if fields.get("transport_state") == "serial":
            fields = dict(fields)
            fields["transport_state"] = "idle"
            fields["active"] = False
            fields["active_failure"] = "ROARM_SERIAL_REJECTED"
            fields["failure_detail"] = "USB/serial is not a RoArm runtime path"
        directory = Path(self.stop_path).parent
        path = self._status_path()
        current = {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except (OSError, ValueError, TypeError):
            current = {}
        current.update(fields)
        if self.pattern_name:
            current["pattern"] = self.pattern_name
        current["serial_fallback"] = False
        current["udp_target"] = f"{TRAJECTORY_ARM_IP}:{TRAJECTORY_UDP_PORT}"
        if current.get("transport_state") not in ("idle", "http", "udp"):
            current["transport_state"] = "idle"
        current["updated_at"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        try:
            directory.mkdir(parents=True, exist_ok=True)
            _write_json_atomic(path, current)
        except OSError:
            return

    def _publish_stream_end(self, sid, last_seq, sent_any):
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        fields = {
            "transport_state": "idle",
            "active": False,
            "stream_id": sid,
            "last_sequence": last_seq,
        }
        if self.error == "PATTERN_UDP_LATE":
            fields["active_failure"] = "PATTERN_UDP_LATE"
            fields["failure_detail"] = self.error_detail
            fields["last_late"] = {
                "at": stamp,
                "sequence": last_seq,
                "detail": self.error_detail,
            }
        elif self.error == "PATTERN_UDP_FAILED":
            fields["active_failure"] = "PATTERN_UDP_FAILED"
            fields["failure_detail"] = self.error_detail
            fields["last_failed"] = {
                "at": stamp,
                "sequence": last_seq,
                "detail": self.error_detail,
            }
        elif self.error is None and sent_any:
            fields["active_failure"] = None
            fields["failure_detail"] = None
            fields["last_completion"] = {
                "at": stamp,
                "pattern": self.pattern_name,
                "stream_id": sid,
                "sequence": last_seq,
            }
        self._publish_transport(**fields)

    def _execute_http(self, steps):
        self._publish_transport(transport_state="http", active=True)
        for step in steps:
            if self._stopped():
                self.stopped = True
                self.error = "PATTERN_STOP_REQUESTED"
                return
            kind = step[0]
            if kind == "packet":
                self._send(step[1])
                if self.error:
                    return
                if step[2]:
                    self.sleep_fn(step[2])
            elif kind == "wait_base":
                self._wait_base(step[1], step[2], step[3])
                if self.error:
                    return
            else:
                self.error = "PACKET_NOT_IN_PATTERN"
                raise PatternClosed(self.error)

    def _execute_udp(self, steps):
        try:
            index = 0
            while index < len(steps):
                if self._stopped():
                    self.stopped = True
                    self.error = "PATTERN_STOP_REQUESTED"
                    return
                step = steps[index]
                if step[0] != "packet":
                    self.error = "PACKET_NOT_IN_PATTERN"
                    raise PatternClosed(self.error)
                packet = step[1]
                if isinstance(packet, dict) and packet.get("T") == 105:
                    if step[2]:
                        self.sleep_fn(step[2])
                    index += 1
                    continue
                if isinstance(packet, dict) and packet.get("T") == 1041:
                    run_end = index + 1
                    while (
                        run_end < len(steps)
                        and steps[run_end][0] == "packet"
                        and isinstance(steps[run_end][1], dict)
                        and steps[run_end][1].get("T") == 1041
                    ):
                        run_end += 1
                    sent_any = self._stream_t1041(steps[index:run_end])
                    index = run_end
                    if self.error == "PATTERN_STOP_REQUESTED":
                        return
                    if sent_any:
                        self.sleep_fn(TRAJECTORY_RELEASE_WAIT_S)
                    if self.error in ("PATTERN_UDP_FAILED", "PATTERN_UDP_LATE"):
                        continue
                    if self.error:
                        return
                    continue
                self._publish_transport(transport_state="http", active=True)
                self._send(packet)
                if self.error:
                    return
                if step[2]:
                    self.sleep_fn(step[2])
                index += 1
        finally:
            self.udp_link.close()

    def _stream_t1041(self, steps):
        """Send one contiguous T1041 run. Returns whether any datagram was sent."""
        sent_any = False
        try:
            self.udp_link.open()
            sid = self.udp_link.allocate_sid()
        except Exception as exc:
            self.error = "PATTERN_UDP_FAILED"
            self.error_detail = str(exc)
            self._publish_stream_end(None, None, False)
            return False
        self._publish_transport(
            transport_state="udp",
            active=True,
            stream_id=sid,
            last_sequence=None,
            active_failure=None,
            failure_detail=None,
        )
        origin = self.clock()
        last_seq = None
        try:
            for index, step in enumerate(steps):
                if self._stopped():
                    self.stopped = True
                    self.error = "PATTERN_STOP_REQUESTED"
                    return sent_any
                packet = step[1]
                if not isinstance(packet, dict) or packet.get("T") != 1041:
                    self.error = "PACKET_NOT_IN_PATTERN"
                    return sent_any
                cadence = float(step[2])
                target = origin + index * cadence
                now = self.clock()
                if cadence > 0 and now > target + cadence:
                    self.error = "PATTERN_UDP_LATE"
                    self.error_detail = (
                        f"sequence {index} is behind by {now - target:.3f}s"
                    )
                    return sent_any
                if now < target:
                    self.sleep_fn(target - now)
                try:
                    self.udp_link.send_point(packet, sid, index)
                except Exception as exc:
                    self.error = "PATTERN_UDP_FAILED"
                    self.error_detail = str(exc)
                    return sent_any
                sent_any = True
                last_seq = index
                self.sent.append(packet)
                if packet.get("T") in _ARM_T:
                    self.arm_packets += 1
            return sent_any
        finally:
            self._publish_stream_end(sid, last_seq, sent_any)

    def _send(self, packet):
        if not isinstance(packet, dict) or packet.get("T") not in _ALLOWED_T:
            self.error = "PACKET_NOT_IN_PATTERN"
            raise PatternClosed(self.error)
        if packet.get("T") == 210 and packet.get("cmd") not in (0, 1):
            self.error = "PACKET_NOT_IN_PATTERN"
            raise PatternClosed(self.error)
        try:
            self.client._get(packet)
        except Exception as exc:
            self.error = "PATTERN_HTTP_FAILED"
            self.error_detail = str(exc)
            raise PatternClosed(self.error) from exc
        self.sent.append(packet)
        if packet.get("T") in _ARM_T:
            self.arm_packets += 1

    def _wait_base(self, target, tolerance, timeout_s):
        deadline = self.clock() + timeout_s
        while True:
            if self._stopped():
                self.stopped = True
                self.error = "PATTERN_STOP_REQUESTED"
                return
            if self.clock() > deadline:
                self.error = "PATTERN_WAIT_TIMEOUT"
                self.error_detail = f"base did not reach {target}"
                raise PatternClosed(self.error)
            try:
                response = self.client._get({"T": 105})
            except Exception as exc:
                self.error = "PATTERN_HTTP_FAILED"
                self.error_detail = str(exc)
                raise PatternClosed(self.error) from exc
            self.sent.append({"T": 105})
            actual = response.get(_BASE_KEY) if isinstance(response, dict) else None
            if (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and abs(float(actual) - target) <= tolerance
            ):
                return
            self.sleep_fn(0.15)


def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid(runtime_dir):
    try:
        return int(
            (Path(runtime_dir) / "pattern.pid").read_text(encoding="utf-8").strip()
        )
    except (OSError, ValueError):
        return None


def _signal_pid(pid):
    os.kill(pid, signal.SIGTERM)


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _discrete_t104(pose):
    """One Cartesian T104 using the existing discrete-pose fields."""
    if not isinstance(pose, dict):
        return None
    packet = {"T": 104}
    for key in ("x", "y", "z"):
        if not _finite_number(pose.get(key)):
            return None
        packet[key] = float(pose[key])
    for key, default in (("t", 0.0), ("r", 0.0), ("spd", 0.5)):
        value = pose.get(key, default)
        if not _finite_number(value):
            return None
        packet[key] = float(value)
    return packet


def _run_http_steps(
    steps,
    *,
    command,
    pattern_name,
    route_text,
    state_reader,
    sleep_fn,
    clock,
    transport_factory,
    runtime_dir,
    pid_alive,
):
    """One existing HTTP session. No UDP socket and no serial device."""
    runtime = Path(runtime_dir)
    running = _read_pid(runtime)
    if running is not None and pid_alive(running):
        return _refused(
            "PATTERN_ALREADY_RUNNING",
            command=command,
            pattern=pattern_name,
            pid=running,
        )
    if route_text is None:
        route_text = read_arm_route()
    refused = evaluate_arm_route(route_text)
    if refused is not None:
        result = _refused(
            refused["reason"],
            command=command,
            pattern=pattern_name,
            arm_route=refused.get("arm_route"),
        )
        result["sequence_status"] = "STOPPED_ARM_ROUTE"
        return result
    adapter = ProductionMotionAdapter(
        state_reader=state_reader,
        sleep_fn=sleep_fn,
    )
    state, denied, attempts = _fresh_t105_preflight(adapter)
    fresh = (
        isinstance(state, dict)
        and state.get("connected") is True
        and state.get("fresh") is True
    )
    if denied is not None or not fresh:
        return _refused(
            "PREFLIGHT_UNAVAILABLE",
            command=command,
            pattern=pattern_name,
            preflight_attempts=attempts,
            preflight_reason=None if denied is None else denied.get("reason"),
        )
    runtime.mkdir(parents=True, exist_ok=True)
    stop_path = runtime / "stop"
    stop_path.unlink(missing_ok=True)
    pid_path = runtime / "pattern.pid"
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    client = None
    session = None
    final_t105 = None
    final_t105_error = None
    try:
        if transport_factory is None:
            from runtime.core.transport.roarm_http import RoArmHttpClient

            client = RoArmHttpClient(
                os.environ.get("ROARM_HTTP_BASE_URL", "http://192.168.4.1")
            )
        else:
            client = transport_factory()
        session = PatternHttpSession(
            client,
            stop_path,
            sleep_fn,
            clock,
            udp_link=None,
            pattern_name=pattern_name,
        )
        try:
            session.execute(steps)
        except PatternClosed:
            pass
        final_t105, final_t105_error = _read_final_t105(client)
    finally:
        pid_path.unlink(missing_ok=True)
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                close()
    sent = 0 if session is None else len(session.sent)
    arm = 0 if session is None else session.arm_packets
    outcome = {
        "authorized": True,
        "command": command,
        "pattern": pattern_name,
        "position_verified": False,
        "settled_claim": False,
        "preflight_attempts": attempts,
        "preflight_fresh": True,
        "packets_sent": sent,
        "motion_packets_sent": arm,
        "torque_off_sent": False,
        "final_t105": final_t105,
        "final_t105_error": final_t105_error,
        "serial_opened": False,
        "udp_opened": False,
        "transport": "http",
    }
    if session is not None and session.error == "PATTERN_STOP_REQUESTED":
        outcome.update(
            ok=False,
            stopped=True,
            reason="PATTERN_STOP_REQUESTED",
            hardware_action="PATTERN_STOPPED" if arm else "NONE",
        )
        return outcome
    if session is not None and session.error:
        outcome.update(
            ok=False,
            reason=session.error,
            error=session.error_detail,
            hardware_action="PATTERN_OUTCOME_UNCERTAIN" if arm else "NONE",
        )
        return outcome
    outcome.update(ok=True, reason="PATTERN_FINISHED", hardware_action="PATTERN_HTTP_SENT")
    return outcome


def execute_discrete_pose(
    pose,
    *,
    route_text=None,
    state_reader=None,
    sleep_fn=None,
    clock=None,
    transport_factory=None,
    runtime_dir=RUNTIME_DIR,
    pid_alive=_pid_alive,
):
    """Send one existing HTTP T104. Does not open the UDP trajectory path."""
    if _pattern_pi_entry_depth == 0:
        return _refused("LOCAL_PATTERN_REFUSED", command="pose")
    packet = _discrete_t104(pose)
    if packet is None:
        return _refused("MALFORMED_POSE", command="pose")
    return _run_http_steps(
        [("packet", packet, 0.0)],
        command="pose",
        pattern_name="move_to_pose",
        route_text=route_text,
        state_reader=state_reader,
        sleep_fn=time.sleep if sleep_fn is None else sleep_fn,
        clock=time.perf_counter if clock is None else clock,
        transport_factory=transport_factory,
        runtime_dir=runtime_dir,
        pid_alive=pid_alive,
    )


def execute_engineering_packet(
    packet,
    *,
    route_text=None,
    state_reader=None,
    sleep_fn=None,
    clock=None,
    transport_factory=None,
    runtime_dir=RUNTIME_DIR,
    pid_alive=_pid_alive,
):
    """One HTTP packet on the existing discrete plane. Not a UDP stream."""
    if _pattern_pi_entry_depth == 0:
        return _refused("LOCAL_PATTERN_REFUSED", command="engineering")
    if not isinstance(packet, dict) or packet.get("T") not in (_ALLOWED_T - {1041}):
        return _refused("PACKET_NOT_IN_HTTP_PLANE", command="engineering")
    return _run_http_steps(
        [("packet", packet, 0.0)],
        command="engineering",
        pattern_name="engineering",
        route_text=route_text,
        state_reader=state_reader,
        sleep_fn=time.sleep if sleep_fn is None else sleep_fn,
        clock=time.perf_counter if clock is None else clock,
        transport_factory=transport_factory,
        runtime_dir=runtime_dir,
        pid_alive=pid_alive,
    )


def execute_pattern_locally(
    argv,
    *,
    route_text=None,
    state_reader=None,
    sleep_fn=None,
    clock=None,
    transport_factory=None,
    pattern_root=PATTERN_ROOT,
    runtime_dir=RUNTIME_DIR,
    pid_alive=_pid_alive,
    signal_pid=_signal_pid,
    udp_socket_factory=None,
    stream_id_factory=None,
):
    """Run one allowlisted command. Motion requires the Pi entry."""
    parsed = _parse(argv)
    if parsed is None:
        return _refused(
            "UNKNOWN_PATTERN_COMMAND",
            patterns=list(REGISTRY),
        )
    command, pattern = parsed
    if command == "list":
        return {
            "ok": True,
            "command": "list",
            "patterns": command_inventory(),
            "hardware_action": "NONE",
        }
    if _pattern_pi_entry_depth == 0:
        return _refused(
            "LOCAL_PATTERN_REFUSED",
            command=command,
            pattern=pattern,
        )
    if command == "stop":
        return _stop_locally(
            runtime_dir=runtime_dir,
            pid_alive=pid_alive,
            signal_pid=signal_pid,
        )
    if command == "torque-off":
        return _torque_off_locally(
            route_text=route_text,
            transport_factory=transport_factory,
            runtime_dir=runtime_dir,
        )
    result = _run_locally(
        pattern,
        route_text=route_text,
        state_reader=state_reader,
        sleep_fn=time.sleep if sleep_fn is None else sleep_fn,
        clock=time.perf_counter if clock is None else clock,
        transport_factory=transport_factory,
        pattern_root=pattern_root,
        runtime_dir=runtime_dir,
        pid_alive=pid_alive,
        udp_socket_factory=udp_socket_factory,
        stream_id_factory=stream_id_factory,
    )
    if isinstance(result, dict):
        result["transport"] = pattern_transport(pattern)
        result.setdefault("serial_opened", False)
        result.setdefault("udp_opened", False)
    return result


def _run_locally(
    pattern,
    *,
    route_text,
    state_reader,
    sleep_fn,
    clock,
    transport_factory,
    pattern_root,
    runtime_dir,
    pid_alive,
    udp_socket_factory,
    stream_id_factory,
):
    runtime = Path(runtime_dir)
    running = _read_pid(runtime)
    if running is not None and pid_alive(running):
        return _refused(
            "PATTERN_ALREADY_RUNNING",
            command="run",
            pattern=pattern,
            pid=running,
        )
    try:
        steps = load_steps(pattern, pattern_root)
    except FileNotFoundError as exc:
        return _refused(
            "PATTERN_SCRIPT_MISSING",
            command="run",
            pattern=pattern,
            script=str(exc),
        )
    except (OSError, ValueError, StopIteration) as exc:
        return _refused(
            "PATTERN_SOURCE_UNREADABLE",
            command="run",
            pattern=pattern,
            error=str(exc),
        )
    if route_text is None:
        route_text = read_arm_route()
    refused = evaluate_arm_route(route_text)
    if refused is not None:
        result = _refused(
            refused["reason"],
            command="run",
            pattern=pattern,
            arm_route=refused.get("arm_route"),
        )
        result["sequence_status"] = "STOPPED_ARM_ROUTE"
        return result

    adapter = ProductionMotionAdapter(
        state_reader=state_reader,
        sleep_fn=sleep_fn,
    )
    state, denied, attempts = _fresh_t105_preflight(adapter)
    fresh = (
        isinstance(state, dict)
        and state.get("connected") is True
        and state.get("fresh") is True
    )
    if denied is not None or not fresh:
        return _refused(
            "PREFLIGHT_UNAVAILABLE",
            command="run",
            pattern=pattern,
            preflight_attempts=attempts,
            preflight_reason=None if denied is None else denied.get("reason"),
        )

    runtime.mkdir(parents=True, exist_ok=True)
    stop_path = runtime / "stop"
    stop_path.unlink(missing_ok=True)
    pid_path = runtime / "pattern.pid"
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    client = None
    session = None
    udp_link = None
    final_t105 = None
    final_t105_error = None
    try:
        if transport_factory is None:
            from runtime.core.transport.roarm_http import RoArmHttpClient

            client = RoArmHttpClient(
                os.environ.get("ROARM_HTTP_BASE_URL", "http://192.168.4.1")
            )
        else:
            client = transport_factory()
        if pattern_transport(pattern) == "udp":
            udp_link = TrajectoryUdpLink(
                trajectory_udp_address(),
                udp_socket_factory or _default_udp_socket,
                stream_id_factory,
            )
        session = PatternHttpSession(
            client, stop_path, sleep_fn, clock, udp_link=udp_link, pattern_name=pattern
        )
        try:
            session.execute(steps)
        except PatternClosed:
            pass
        final_t105, final_t105_error = _read_final_t105(client)
    finally:
        pid_path.unlink(missing_ok=True)
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                close()

    sent = 0 if session is None else len(session.sent)
    arm = 0 if session is None else session.arm_packets
    source = REGISTRY[pattern]["source"]
    outcome = {
        "authorized": True,
        "command": "run",
        "pattern": pattern,
        "script": source,
        "position_verified": False,
        "settled_claim": False,
        "preflight_attempts": attempts,
        "preflight_fresh": True,
        "packets_sent": sent,
        "motion_packets_sent": arm,
        "torque_off_sent": False,
        "final_t105": final_t105,
        "final_t105_error": final_t105_error,
        "serial_opened": False,
        "udp_opened": bool(udp_link is not None and udp_link.opened),
        "udp_target": (
            None
            if udp_link is None
            else {"host": udp_link.address[0], "port": udp_link.address[1]}
        ),
        "udp_stream_id": None if udp_link is None else udp_link.sid,
    }
    if session is not None and session.error == "PATTERN_STOP_REQUESTED":
        outcome.update(
            ok=False,
            reason="PATTERN_STOP_REQUESTED",
            hardware_action="PATTERN_STOPPED" if arm else "NONE",
        )
        return outcome
    if session is not None and session.error:
        outcome.update(
            ok=False,
            reason=session.error,
            error=session.error_detail,
            hardware_action="PATTERN_OUTCOME_UNCERTAIN" if arm else "NONE",
        )
        return outcome
    outcome.update(
        ok=True,
        reason="PATTERN_FINISHED",
        hardware_action=(
            "PATTERN_UDP_SENT" if udp_link is not None else "PATTERN_HTTP_SENT"
        ),
    )
    return outcome


def _read_final_t105(client):
    """One read after the pattern. Not a motion packet and not retried."""
    try:
        feedback = client._get({"T": 105})
    except Exception as exc:
        return None, str(exc)
    if not isinstance(feedback, dict) or feedback.get("T") != 1051:
        return feedback, "T105_READBACK_INVALID"
    return feedback, None


def _stop_locally(*, runtime_dir, pid_alive, signal_pid):
    """Stop further points. Torque stays enabled. No arm packet is sent."""
    runtime = Path(runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "stop").write_text("stop\n", encoding="utf-8")
    pid = _read_pid(runtime)
    signaled = False
    if pid is not None and pid_alive(pid):
        signal_pid(pid)
        signaled = True
    return {
        "ok": True,
        "authorized": True,
        "command": "stop",
        "pattern": None,
        "reason": "STOP_REQUESTED",
        "hardware_action": "NONE",
        "position_verified": False,
        "settled_claim": False,
        "packets_sent": 0,
        "motion_packets_sent": 0,
        "pattern_process_signaled": signaled,
        "torque_off_sent": False,
    }


def _torque_off_locally(*, route_text, transport_factory, runtime_dir):
    """Explicit torque-off. One T210 cmd 0 after the route check. No retry."""
    del runtime_dir
    if route_text is None:
        route_text = read_arm_route()
    refused = evaluate_arm_route(route_text)
    if refused is not None:
        result = _refused(
            refused["reason"],
            command="torque-off",
            arm_route=refused.get("arm_route"),
        )
        result["torque_off_sent"] = False
        return result

    client = None
    try:
        if transport_factory is None:
            from runtime.core.transport.roarm_http import RoArmHttpClient

            client = RoArmHttpClient(
                os.environ.get("ROARM_HTTP_BASE_URL", "http://192.168.4.1")
            )
        else:
            client = transport_factory()
        client._get({"T": 210, "cmd": 0})
    except Exception as exc:
        return {
            "ok": False,
            "authorized": True,
            "command": "torque-off",
            "pattern": None,
            "reason": "TORQUE_OFF_NOT_DELIVERED",
            "hardware_action": "TORQUE_OFF_NOT_DELIVERED",
            "position_verified": False,
            "settled_claim": False,
            "packets_sent": 0,
            "motion_packets_sent": 0,
            "torque_off_sent": False,
            "error": str(exc),
        }
    finally:
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                close()
    return {
        "ok": True,
        "authorized": True,
        "command": "torque-off",
        "pattern": None,
        "reason": "TORQUE_OFF_SENT",
        "hardware_action": "TORQUE_OFF_SENT",
        "position_verified": False,
        "settled_claim": False,
        "packets_sent": 1,
        "motion_packets_sent": 0,
        "torque_off_sent": True,
    }


def _ssh_command(host, remote_command):
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "--",
        host,
        remote_command,
    ]


def _output_text(completed):
    stdout = completed.stdout or b""
    stderr = completed.stderr or b""
    if isinstance(stdout, str):
        out = stdout
        err = stderr if isinstance(stderr, str) else ""
    else:
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
    return out, err


def _cli_is_on_pi():
    """The Pi runs the command in this process. Windows SSH-dispatches."""
    return sys.platform != "win32"


def _pi_local_command(argv, **local_options):
    """Same entry the SSH remote uses: scope, route, then fresh T105."""
    with pattern_pi_entry_scope():
        return execute_pattern_locally(list(argv), **local_options)


def dispatch_pattern_command(argv, *, runner=None, on_pi=None, **local_options):
    """Run on the Pi. Windows copies the tree over SSH first.

    A command already running on the Pi stays in this process.
    `list` and an unknown command do not open SSH or HTTP.
    """
    parsed = _parse(argv)
    if parsed is None:
        return _refused(
            "UNKNOWN_PATTERN_COMMAND",
            patterns=list(REGISTRY),
        )
    command, pattern = parsed
    if command == "list":
        return {
            "ok": True,
            "command": "list",
            "patterns": command_inventory(),
            "hardware_action": "NONE",
        }
    if _cli_is_on_pi() if on_pi is None else on_pi:
        return _pi_local_command(argv, **local_options)
    if local_options:
        raise TypeError("local options are only used when already on the Pi")
    runner = _default_runner if runner is None else runner
    host = ssh_host()
    archive = build_tree_archive()
    sync = runner(
        _ssh_command(
            host,
            f"rm -rf {REMOTE_TREE} && mkdir -p {REMOTE_TREE} && "
            f"tar -xzf - -C {REMOTE_TREE}",
        ),
        input_bytes=archive,
        timeout_s=60,
    )
    if sync.returncode != 0:
        _out, err = _output_text(sync)
        return _refused(
            "PI_EXECUTION_FAILED",
            command=command,
            pattern=pattern,
            error=(err or _out or "Pi tree sync failed")[-4000:],
        )
    remote = (
        f"cd {REMOTE_TREE} && {LOCAL_EXECUTION_ENV}=1 "
        f"python3 {_ENTRY} {' '.join(argv)}"
    )
    completed = runner(
        _ssh_command(host, remote),
        input_bytes=None,
        timeout_s=_RUN_TIMEOUT_S,
    )
    out, err = _output_text(completed)
    if completed.returncode != 0:
        return _refused(
            "PI_EXECUTION_FAILED",
            command=command,
            pattern=pattern,
            error=(err or out or "Pi pattern process failed")[-4000:],
        )
    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        return _refused(
            "PI_EXECUTION_FAILED",
            command=command,
            pattern=pattern,
            error=(err or out or "Pi pattern command returned no JSON")[-4000:],
        )
    if not isinstance(result, dict):
        return _refused(
            "PI_EXECUTION_FAILED",
            command=command,
            pattern=pattern,
            error="Pi pattern command returned a non-object result",
        )
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["list"]:
        sys.stdout.write(format_inventory() + "\n")
        return 0
    result = dispatch_pattern_command(argv)
    json.dump(result, sys.stdout, default=str)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
