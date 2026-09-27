"""Pi-side entry for allowlisted pattern commands.

The host runner sets ROARM_PATTERN_EXECUTE_LOCAL=1. This process then
checks the arm route and a fresh T105 before any pattern HTTP request.
"""
import json
import os
import sys
from pathlib import Path


LOCAL_EXECUTION_ENV = "ROARM_PATTERN_EXECUTE_LOCAL"


def _repository_root():
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        marker = (
            candidate / "runtime" / "core" / "safety" / "production_motion.py"
        )
        if marker.is_file():
            return candidate
    return None


def main():
    if os.environ.get(LOCAL_EXECUTION_ENV) != "1":
        raise SystemExit(
            "Pi pattern entry refused. No hardware request was sent."
        )
    root = _repository_root()
    if root is None:
        raise SystemExit(
            "Repository root not found. No hardware request was sent."
        )
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from runtime.core.safety.pattern_commands import (
        execute_pattern_locally,
        pattern_pi_entry_scope,
    )

    with pattern_pi_entry_scope():
        result = execute_pattern_locally(sys.argv[1:])
    json.dump(result, sys.stdout, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
