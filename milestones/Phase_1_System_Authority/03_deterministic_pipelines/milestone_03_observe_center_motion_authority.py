"""Compatibility wrapper for the physically verified Observe Center pose."""
from runtime.core.safety.production_motion import execute_named_pose


# Human-taught physical values are retained exactly.
TARGETS = {
    "base": -0.030679616,
    "shoulder": -0.832951568,
    "elbow": 2.460505184,
    "wrist": 0.004601942,
    "roll": 0.001533981,
    "hand": 3.146194596,
}


def arm_observe_center():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_observe_center():
    return execute_named_pose("observe_center", TARGETS)
