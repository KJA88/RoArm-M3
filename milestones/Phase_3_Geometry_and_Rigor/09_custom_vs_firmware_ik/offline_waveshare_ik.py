"""Offline IK comparison for the four commanded T104 targets. No hardware.

Settled joints are T105 readbacks from the live probes. T105 Cartesian values
are firmware reports, already shown to match upstream FK of those joints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from waveshare_m3_fk import upstream_fk
from waveshare_m3_ik import fk_of, header_ik, reflected_triangle

ROLL = 0.003067962


@dataclass(frozen=True)
class Joints:
    name: str
    b: float
    s: float
    e: float
    t: float


READY = Joints("READY", -0.001533981, -0.829883606, 2.405281875, 0.016873789)
Z200_SETTLED = Joints("Z200", -0.001533981, -0.394233062, 2.089281833, -0.099708751)
CENTER_CONTROLLED = Joints("CENTER", -0.001533981, -0.391165101, 1.768679848, 0.228563137)
Z300_SETTLED = Joints("Z300", -0.001533981, -0.305262177, 1.339165228, 0.573708815)
X300_SETTLED = Joints("X300", -0.001533981, -0.181009733, 1.61681575, 0.188679637)
# Earlier center readback. Same command, elbow differs by about 0.0015 rad.
CENTER_EARLIER = Joints("CENTER_EARLIER", -0.001533981, -0.391165101, 1.767145868, 0.228563137)

# pre_pose is set only where m05 records the pose the probe started from.
# Z200 and Z300 do not store one, so the continuity check uses READY.
TARGETS = (
    {"name": "CENTER", "x": 250.0, "y": 0.0, "z": 250.0, "pitch": 0.0, "settled": CENTER_CONTROLLED, "pre_pose": Z200_SETTLED},
    {"name": "Z200", "x": 250.0, "y": 0.0, "z": 200.0, "pitch": 0.0, "settled": Z200_SETTLED, "pre_pose": None},
    {"name": "Z300", "x": 250.0, "y": 0.0, "z": 300.0, "pitch": 0.0, "settled": Z300_SETTLED, "pre_pose": None},
    {"name": "X300", "x": 300.0, "y": 0.0, "z": 250.0, "pitch": 0.0, "settled": X300_SETTLED, "pre_pose": CENTER_CONTROLLED},
)


def joint_delta(solution, settled: Joints) -> dict[str, float]:
    return {
        "db": solution.base - settled.b,
        "ds": solution.shoulder - settled.s,
        "de": solution.elbow - settled.e,
        "dt": solution.wrist - settled.t,
    }


def travel(solution, pose: Joints) -> float:
    return abs(solution.shoulder - pose.s) + abs(solution.elbow - pose.e) + abs(solution.wrist - pose.t)


def compare_target(target: dict) -> dict:
    x, y, z, pitch = target["x"], target["y"], target["z"], target["pitch"]
    exposed = header_ik(x, y, z, ROLL, pitch)
    reflected = reflected_triangle(x, y, z, ROLL, pitch)
    rows = []
    for solution in (exposed, reflected):
        if solution.nan_ik:
            rows.append({"label": solution.label, "exposed": solution.exposed_by_header, "nan_ik": True})
            continue
        pose = fk_of(solution)
        settled_fk = upstream_fk(target["settled"].b, target["settled"].s, target["settled"].e, target["settled"].t)
        delta = joint_delta(solution, target["settled"])
        dx = pose[0] - settled_fk[0]
        dy = pose[1] - settled_fk[1]
        dz = pose[2] - settled_fk[2]
        rows.append(
            {
                "label": solution.label,
                "exposed": solution.exposed_by_header,
                "nan_ik": False,
                "base": solution.base,
                "shoulder": solution.shoulder,
                "elbow": solution.elbow,
                "wrist": solution.wrist,
                **delta,
                "fk_x": pose[0],
                "fk_y": pose[1],
                "fk_z": pose[2],
                "fk_pitch": pose[3],
                "fk_to_target_mm": math.dist(pose[:3], (x, y, z)),
                "fk_ik_minus_fk_settled_mm": (dx, dy, dz, math.sqrt(dx * dx + dy * dy + dz * dz)),
                "travel_from_ready": travel(solution, READY),
                "travel_from_pre_pose": None if target["pre_pose"] is None else travel(solution, target["pre_pose"]),
            }
        )
    finite = [row for row in rows if not row["nan_ik"]]
    nearer_ready = min(finite, key=lambda row: row["travel_from_ready"])
    nearer_pre = None
    if target["pre_pose"] is not None:
        nearer_pre = min(finite, key=lambda row: row["travel_from_pre_pose"])["label"]
    return {
        "name": target["name"],
        "pre_pose": None if target["pre_pose"] is None else target["pre_pose"].name,
        "branches": rows,
        "nearer_ready": nearer_ready["label"],
        "nearer_pre_pose": nearer_pre,
    }


def all_comparisons():
    return [compare_target(target) for target in TARGETS]


def earlier_center_elbow_delta() -> float:
    exposed = header_ik(250.0, 0.0, 250.0, ROLL, 0.0)
    return exposed.elbow - CENTER_EARLIER.e


def format_report() -> str:
    lines = []
    for item in all_comparisons():
        lines.append(f"{item['name']} pre_pose={item['pre_pose']} nearer_ready={item['nearer_ready']} nearer_pre={item['nearer_pre_pose']}")
        for branch in item["branches"]:
            if branch["nan_ik"]:
                lines.append(f"  {branch['label']} nan exposed={branch['exposed']}")
                continue
            dx, dy, dz, norm = branch["fk_ik_minus_fk_settled_mm"]
            lines.append(
                f"  {branch['label']} exposed={branch['exposed']} "
                f"b={branch['base']:.6f} s={branch['shoulder']:.6f} e={branch['elbow']:.6f} t={branch['wrist']:.6f}"
            )
            lines.append(
                f"    db={branch['db']:+.6f} ds={branch['ds']:+.6f} de={branch['de']:+.6f} dt={branch['dt']:+.6f} "
                f"fk_to_target={branch['fk_to_target_mm']:.6f} "
                f"cart_vs_settled=({dx:+.3f},{dy:+.3f},{dz:+.3f}) norm={norm:.3f} "
                f"from_ready={branch['travel_from_ready']:.4f} from_pre={branch['travel_from_pre_pose']}"
            )
    lines.append(f"earlier center elbow residual vs header IK: {earlier_center_elbow_delta():+.6f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report())
