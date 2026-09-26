"""Production skill: READY, then the authorized center task target."""
from runtime.core.safety.production_motion import (
    execute_ready_approach_center as _execute,
)


def execute_ready_approach_center():
    return _execute()


__all__ = ["execute_ready_approach_center"]
