"""Compatibility entry point for the fixed production center probe."""
from runtime.core.safety.production_motion import (
    execute_named_task_probe as _execute,
)


def execute_task_probe_center():
    return _execute("task_probe_center")


def execute_task_probe_z300():
    return _execute("task_probe_z300")


__all__ = ["execute_task_probe_center", "execute_task_probe_z300"]
