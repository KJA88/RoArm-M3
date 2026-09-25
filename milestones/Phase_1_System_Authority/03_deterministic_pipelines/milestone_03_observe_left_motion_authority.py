"""Compatibility wrapper for the physically verified Observe Left pose."""
from runtime.core.safety.production_motion import execute_named_pose


# Human-taught physical values are retained exactly.
TARGETS = {
    "base": 1.610679827,
    "shoulder": -0.832951568,
    "elbow": 2.411417799,
    "wrist": 0.006135923,
    "roll": 0.0,
    "hand": 3.152330519,
}


def arm_observe_left():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_left():
    return execute_named_pose("observe_left", TARGETS)
