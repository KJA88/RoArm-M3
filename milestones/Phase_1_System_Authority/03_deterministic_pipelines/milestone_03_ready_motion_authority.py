"""Compatibility wrapper for the physically verified Ready pose."""
from runtime.core.safety.production_motion import execute_named_pose


# Human-taught physical values are retained exactly.
READY_TARGETS = {
    "base": 0.001533981,
    "shoulder": -0.832951568,
    "elbow": 2.399145952,
    "wrist": 0.004601942,
    "roll": 0.0,
    "hand": 3.163068385,
}


def arm_ready():
    return {
        "armed": False,
        "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION",
        "sha256": None,
    }


def execute_ready():
    return execute_named_pose("ready", READY_TARGETS)
