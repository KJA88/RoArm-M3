"""Skill-facing entry above the existing pattern command layer.

Named runs and stop call the existing allowlisted command path.
A single explicit pose is one HTTP T104. Nothing here opens UDP itself;
continuous patterns still go through the sequenced UDP sender.
"""
from runtime.core.safety.pattern_commands import (
    execute_discrete_pose,
    execute_engineering_packet,
    execute_pattern_locally,
    pattern_pi_entry_scope,
)

TRAJECTORY_PATTERNS = ("lissajous", "circle", "spiral")
HOME_PATTERN = "home"


def run_named(name, **options):
    with pattern_pi_entry_scope():
        return execute_pattern_locally(["run", name], **options)


def stop_motion(**options):
    with pattern_pi_entry_scope():
        return execute_pattern_locally(["stop"], **options)


def move_pose(pose, **options):
    with pattern_pi_entry_scope():
        return execute_discrete_pose(pose, **options)


def engineering(packet, **options):
    with pattern_pi_entry_scope():
        return execute_engineering_packet(packet, **options)
