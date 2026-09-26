"""Compatibility wrapper for the physically verified scan-left sequence."""
from runtime.core.safety.production_motion import execute_named_sequence


READY_TARGETS = {
    "base": 0.001533981,
    "shoulder": -0.832951568,
    "elbow": 2.399145952,
    "wrist": 0.004601942,
    "roll": 0.0,
    "hand": 3.163068385,
}
LEFT_BASE_TARGET = {"base": 1.610679827}


def arm_scan_left():
    return {"armed": False, "reason": "LOCAL_PERMITS_ISSUED_DURING_EXECUTION", "sha256": None}


def execute_scan_left():
    return execute_named_sequence(
        "scan_left",
        (("ready", READY_TARGETS), ("scan_left", LEFT_BASE_TARGET)),
    )
