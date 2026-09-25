"""Append-only local audit records for motion authorization and execution."""
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock


DEFAULT_AUDIT_PATH = (
    Path(__file__).resolve().parents[2] / "motion_audit.jsonl"
)


class MotionAuditLog:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_AUDIT_PATH
        self._lock = Lock()

    def record(self, event, **details):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "event": event,
            **details,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line)
        return entry


__all__ = ["DEFAULT_AUDIT_PATH", "MotionAuditLog"]
