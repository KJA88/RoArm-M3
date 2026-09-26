"""Compatibility entry point for the fixed production center probe."""
from runtime.core.safety.production_motion import (
    execute_task_probe_center as _execute,
)


def execute_task_probe_center():
    return _execute()


__all__ = ["execute_task_probe_center"]
