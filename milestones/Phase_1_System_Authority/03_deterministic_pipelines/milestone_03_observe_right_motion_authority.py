"""Compatibility wrapper for the physically verified Observe Right pose."""
from runtime.core.safety.production_motion import execute_named_pose


# Human-taught physical values are retained exactly.
TARGETS = {
    "base": -1.578466231,
    "shoulder": -0.832951568,
    "elbow": 2.458971203,
    "wrist": 0.001533981,
    "roll": 0.010737866,
    "hand": 3.143126634,
}


def arm_observe_right():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_right():
    return execute_named_pose("observe_right", TARGETS)
