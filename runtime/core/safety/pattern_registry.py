"""Allowlisted poses and patterns.

Point values are read from the existing scripts. Those scripts are not
imported and their serial transport is not called. The parametric
equations below are the same ones already in the lesson files.
"""
import ast
import math
from pathlib import Path


PATTERN_ROOT = Path("/home/KA_PI/robotics/roarm-m3")

# Present on the Pi, deliberately not commands.
# combined starts other scripts. constant-speed has no script.
# circle_path is continuous joint velocity (T123), not a point list.
# gripper presets and arbitrary joint moves are not arm patterns.
EXCLUDED = (
    {
        "name": "combined",
        "source": "lessons/01_trajectory_and_gripper/demo_combined.py",
        "reason": "starts the lissajous and spiral scripts itself",
    },
    {
        "name": "lissajous_constant_speed",
        "source": "lessons/01_trajectory_and_gripper/demo_lissajous_constant_speed.py",
        "reason": "named in the lesson README, script is not on the Pi",
    },
    {
        "name": "circle_velocity",
        "source": "archive/_safe_backup/archive/circle_path.py",
        "reason": "continuous T123 joint velocity, not the Cartesian circle",
    },
)


def _source(root, relative):
    path = (Path(root) / relative).resolve()
    root_resolved = Path(root).resolve()
    if not path.is_relative_to(root_resolved):
        raise ValueError(f"pattern source escaped {root_resolved}")
    if not path.is_file():
        raise FileNotFoundError(relative)
    return path


def module_literals(path, names):
    """Read module-level constant assignments. Does not execute the file."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found = {}
    wanted = set(names)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Tuple) and isinstance(value, tuple):
            for elt, item in zip(target.elts, value):
                if isinstance(elt, ast.Name) and elt.id in wanted:
                    found[elt.id] = item
        elif isinstance(target, ast.Name) and target.id in wanted:
            found[target.id] = value
    missing = wanted - found.keys()
    if missing:
        raise ValueError(
            f"{path} is missing {', '.join(sorted(missing))}"
        )
    return found


def _eval_number(node, env):
    """Numbers, unary minus, and names already bound to numbers."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("not a number")
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_number(node.operand, env)
    if isinstance(node, ast.Name):
        value = env.get(node.id)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(node.id)
        return value
    if isinstance(node, ast.Tuple):
        return tuple(_eval_number(elt, env) for elt in node.elts)
    if isinstance(node, ast.Dict):
        parsed = {}
        for key, val in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise ValueError("pose key")
            parsed[key.value] = _eval_number(val, env)
        return parsed
    raise ValueError("unsupported")


def module_bindings(path):
    """Module assignments, including names used inside pose dicts.

    Does not execute the file. A pose such as ``g: GRIPPER_CMD`` or
    ``t: -1.56`` is resolved from earlier assignments.
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    env = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        try:
            value = _eval_number(node.value, env)
        except (ValueError, TypeError):
            continue
        if isinstance(target, ast.Tuple) and isinstance(value, tuple):
            if len(target.elts) != len(value):
                continue
            for elt, item in zip(target.elts, value):
                if isinstance(elt, ast.Name):
                    env[elt.id] = item
        elif isinstance(target, ast.Name):
            env[target.id] = value
    return env


def _source_order(node):
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _source_order(child)


def literal_command_dicts(path):
    """Return source-order dict literals that contain T. Does not execute."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found = []
    for node in _source_order(tree):
        if not isinstance(node, ast.Dict):
            continue
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and "T" in value:
            found.append(value)
    if not found:
        raise ValueError(f"{path} has no command dict")
    return found


def _packet(command, delay_s=0.0):
    return ("packet", command, float(delay_s))


def _wait_base(target, tolerance, timeout_s):
    return ("wait_base", float(target), float(tolerance), float(timeout_s))


def lissajous_steps(root):
    relative = "lessons/01_trajectory_and_gripper/demo_lissajous.py"
    values = module_literals(
        _source(root, relative),
        {
            "CX", "CY", "CZ", "WIDTH", "HEIGHT", "LENGTH",
            "STEPS", "DT", "GRIPPER_RAD",
        },
    )
    steps = [
        _packet({"T": 210, "cmd": 1}, 0.5),
        _packet(
            {
                "T": 104,
                "x": values["CX"],
                "y": values["CY"],
                "z": values["CZ"],
                "t": 0,
                "r": 0,
                "g": values["GRIPPER_RAD"],
                "spd": 0.5,
            },
            2.0,
        ),
    ]
    steps_n = int(values["STEPS"])
    for i in range(steps_n + 1):
        phi = 2.0 * math.pi * (i / steps_n)
        tx = values["CX"] + (values["LENGTH"] / 2) * math.cos(phi)
        ty = values["CY"] + values["WIDTH"] * math.sin(2 * phi)
        tz = values["CZ"] + values["HEIGHT"] * math.sin(phi)
        tt = 0.3 * math.cos(phi)
        steps.append(
            _packet(
                {
                    "T": 1041,
                    "x": round(tx, 2),
                    "y": round(ty, 2),
                    "z": round(tz, 2),
                    "t": round(tt, 2),
                    "r": 0,
                    "g": values["GRIPPER_RAD"],
                },
                values["DT"],
            )
        )
    steps.append(
        _packet(
            {
                "T": 104,
                "x": 0,
                "y": 0,
                "z": 400,
                "t": 0,
                "r": 0,
                "g": values["GRIPPER_RAD"],
                "spd": 0.5,
            },
            2.0,
        )
    )
    return steps


def spiral_steps(root):
    relative = "lessons/01_trajectory_and_gripper/demo_spiral.py"
    values = module_literals(
        _source(root, relative),
        {
            "CX", "CY", "CZ", "R_START", "R_END",
            "STEPS", "DT", "GRIPPER_RAD",
        },
    )
    steps = [
        _packet({"T": 210, "cmd": 1}, 0.5),
        _packet(
            {
                "T": 104,
                "x": values["CX"] + values["R_START"],
                "y": values["CY"],
                "z": values["CZ"],
                "t": 0,
                "r": 0,
                "g": values["GRIPPER_RAD"],
                "spd": 0.5,
            },
            1.5,
        ),
    ]
    steps_n = int(values["STEPS"])
    for inward in (True, False):
        for i in range(steps_n):
            alpha = i / steps_n
            if inward:
                radius = (1 - alpha) * values["R_START"] + alpha * values["R_END"]
            else:
                radius = (1 - alpha) * values["R_END"] + alpha * values["R_START"]
            theta = 2.0 * math.pi * alpha * 3.0
            steps.append(
                _packet(
                    {
                        "T": 1041,
                        "x": values["CX"] + radius * math.cos(theta),
                        "y": values["CY"] + radius * math.sin(theta),
                        "z": values["CZ"],
                        "t": 0,
                        "r": 0,
                        "g": values["GRIPPER_RAD"],
                    },
                    values["DT"],
                )
            )
    steps.append(_packet({"T": 105}, 0.0))
    return steps


def circle_steps(root):
    relative = "lessons/01_trajectory_and_gripper/_archive/circle_demo.py"
    path = _source(root, relative)
    values = module_bindings(path)
    required = (
        "CX", "CY", "CZ", "R", "AMP", "STEPS", "REVOLUTIONS", "DT",
        "GRIPPER_CMD",
    )
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"{path} is missing {', '.join(missing)}")
    gripper = values["GRIPPER_CMD"]
    steps = [_packet({"T": 210, "cmd": 1}, 0.2)]
    start = values.get("START_POSE")
    if isinstance(start, dict):
        steps.append(
            _packet(
                {
                    "T": 104,
                    "x": start["x"],
                    "y": start["y"],
                    "z": start["z"],
                    "t": start["t"],
                    "r": start["r"],
                    "g": gripper,
                    "spd": start["spd"],
                },
                2.0,
            )
        )
    per_rev = int(values["STEPS"])
    total = per_rev * int(values["REVOLUTIONS"])
    for i in range(total):
        theta = 2.0 * math.pi * (i / per_rev)
        steps.append(
            _packet(
                {
                    "T": 1041,
                    "x": values["CX"] + values["R"] * math.cos(theta),
                    "y": values["CY"] + values["R"] * math.sin(theta),
                    "z": values["CZ"] + values["AMP"] * math.sin(theta),
                    "t": 0.0,
                    "r": 0.0,
                    "g": gripper,
                },
                values["DT"],
            )
        )
    home = values.get("CANDLE_POSE")
    if isinstance(home, dict):
        steps.append(
            _packet(
                {
                    "T": 104,
                    "x": home["x"],
                    "y": home["y"],
                    "z": home["z"],
                    "t": home["t"],
                    "r": home["r"],
                    "g": gripper,
                    "spd": home["spd"],
                },
                2.0,
            )
        )
    steps.append(_packet({"T": 105}, 0.1))
    return steps


def _dicts(root, relative):
    return literal_command_dicts(_source(root, relative))


def candle_steps(root):
    relative = "lessons/01_trajectory_and_gripper/demo_candle.py"
    commands = _dicts(root, relative)
    torque = next(item for item in commands if item.get("T") == 210)
    pose = next(item for item in commands if item.get("T") == 102)
    return [_packet(torque, 0.5), _packet(pose, 2.0)]


def ready_steps(root):
    relative = (
        "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
        "milestone_03_ready_motion_authority.py"
    )
    pose = next(item for item in _dicts(root, relative) if item.get("T") == 102)
    return [_packet(pose, 3.0)]


def home_steps(root):
    relative = (
        "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
        "milestone_03_home_motion_authority.py"
    )
    pose = next(item for item in _dicts(root, relative) if item.get("T") == 100)
    return [_packet(pose, 3.0)]


def _observe(root, filename):
    relative = (
        "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
        + filename
    )
    pose = next(item for item in _dicts(root, relative) if item.get("T") == 102)
    return [_packet(pose, 3.0)]


def observe_center_steps(root):
    return _observe(root, "milestone_03_observe_center_motion_authority.py")


def observe_left_steps(root):
    return _observe(root, "milestone_03_observe_left_motion_authority.py")


def observe_right_steps(root):
    return _observe(root, "milestone_03_observe_right_motion_authority.py")


def _base_move(target, speed, accel):
    return {
        "T": 101,
        "joint": 1,
        "rad": target,
        "spd": speed,
        "acc": accel,
    }


def scan_area_steps(root):
    relative = (
        "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
        "milestone_03_scan_area_motion_authority.py"
    )
    values = module_literals(
        _source(root, relative),
        {"CENTER_BASE", "LEFT_BASE", "RIGHT_BASE", "BASE_SPEED", "BASE_ACCEL"},
    )
    speed = values["BASE_SPEED"]
    accel = values["BASE_ACCEL"]
    sequence = (
        values["CENTER_BASE"],
        values["LEFT_BASE"],
        values["RIGHT_BASE"],
        values["CENTER_BASE"],
    )
    steps = [_packet({"T": 210, "cmd": 1}, 0.0)]
    for target in sequence:
        steps.append(_packet(_base_move(target, speed, accel), 0.0))
        # Same arrival wait the scan script already uses: 0.04 rad, 40 s.
        steps.append(_wait_base(target, 0.04, 40.0))
    return steps


def _scan_side(root, filename, endpoint_name):
    relative = (
        "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
        + filename
    )
    path = _source(root, relative)
    values = module_literals(
        path, {endpoint_name, "SCAN_SPEED", "SCAN_ACCEL"}
    )
    ready = next(
        item for item in literal_command_dicts(path) if item.get("T") == 102
    )
    return [
        _packet({"T": 210, "cmd": 1}, 0.2),
        _packet(ready, 3.0),
        _packet(
            _base_move(
                values[endpoint_name],
                values["SCAN_SPEED"],
                values["SCAN_ACCEL"],
            ),
            5.0,
        ),
    ]


def scan_left_steps(root):
    return _scan_side(
        root, "milestone_03_scan_left_motion_authority.py", "LEFT_BASE"
    )


def scan_right_steps(root):
    return _scan_side(
        root, "milestone_03_scan_right_motion_authority.py", "RIGHT_BASE"
    )


REGISTRY = {
    "lissajous": {
        "kind": "trajectory",
        "source": "lessons/01_trajectory_and_gripper/demo_lissajous.py",
        "steps": lissajous_steps,
    },
    "circle": {
        "kind": "trajectory",
        "source": "lessons/01_trajectory_and_gripper/_archive/circle_demo.py",
        "steps": circle_steps,
    },
    "spiral": {
        "kind": "trajectory",
        "source": "lessons/01_trajectory_and_gripper/demo_spiral.py",
        "steps": spiral_steps,
    },
    "candle": {
        "kind": "pose",
        "source": "lessons/01_trajectory_and_gripper/demo_candle.py",
        "steps": candle_steps,
    },
    "ready": {
        "kind": "pose",
        "source": (
            "milestones/Phase_1_System_Authority/"
            "03_deterministic_pipelines/milestone_03_ready_motion_authority.py"
        ),
        "steps": ready_steps,
    },
    "home": {
        "kind": "pose",
        "source": (
            "milestones/Phase_1_System_Authority/"
            "03_deterministic_pipelines/milestone_03_home_motion_authority.py"
        ),
        "steps": home_steps,
    },
    "observe_center": {
        "kind": "pose",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_observe_center_motion_authority.py"
        ),
        "steps": observe_center_steps,
    },
    "observe_left": {
        "kind": "pose",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_observe_left_motion_authority.py"
        ),
        "steps": observe_left_steps,
    },
    "observe_right": {
        "kind": "pose",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_observe_right_motion_authority.py"
        ),
        "steps": observe_right_steps,
    },
    "scan_area": {
        "kind": "trajectory",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_scan_area_motion_authority.py"
        ),
        "steps": scan_area_steps,
    },
    "scan_left": {
        "kind": "trajectory",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_scan_left_motion_authority.py"
        ),
        "steps": scan_left_steps,
    },
    "scan_right": {
        "kind": "trajectory",
        "source": (
            "milestones/Phase_1_System_Authority/03_deterministic_pipelines/"
            "milestone_03_scan_right_motion_authority.py"
        ),
        "steps": scan_right_steps,
    },
}


def command_inventory():
    return [
        {
            "name": name,
            "kind": spec["kind"],
            "source": spec["source"],
        }
        for name, spec in REGISTRY.items()
    ]


def load_steps(name, root):
    spec = REGISTRY[name]
    return spec["steps"](root)
