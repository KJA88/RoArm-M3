"""Historical RoArm motion evidence; this module does not grant authority."""


REFERENCE_DH_TARGETS = {
    "base": 0.0,
    "shoulder": 1.50,
    "elbow": 0.0,
    "wrist": 0.0,
    "roll": 0.0,
    "hand": 1.0,
}

CANDLE_ARM_TARGETS = {
    "base": 0.0,
    "shoulder": 0.0,
    "elbow": 0.0,
    "wrist": 0.0,
    "roll": 0.0,
}
CANDLE_GRIPPER_EVIDENCE = (1.49, 1.0)

READY_TARGETS = {
    "base": 0.001533981,
    "shoulder": -0.832951568,
    "elbow": 2.399145952,
    "wrist": 0.004601942,
    "roll": 0.0,
    "hand": 3.163068385,
}
OBSERVE_LEFT_TARGETS = {
    "base": 1.610679827,
    "shoulder": -0.832951568,
    "elbow": 2.411417799,
    "wrist": 0.006135923,
    "roll": 0.0,
    "hand": 3.152330519,
}
OBSERVE_CENTER_TARGETS = {
    "base": -0.030679616,
    "shoulder": -0.832951568,
    "elbow": 2.460505184,
    "wrist": 0.004601942,
    "roll": 0.001533981,
    "hand": 3.146194596,
}
OBSERVE_RIGHT_TARGETS = {
    "base": -1.578466231,
    "shoulder": -0.832951568,
    "elbow": 2.458971203,
    "wrist": 0.001533981,
    "roll": 0.010737866,
    "hand": 3.143126634,
}


def _arm_only(targets):
    return {
        joint: targets[joint]
        for joint in ("base", "shoulder", "elbow", "wrist")
    }


READY_ARM_TARGETS = _arm_only(READY_TARGETS)
OBSERVE_LEFT_ARM_TARGETS = _arm_only(OBSERVE_LEFT_TARGETS)
OBSERVE_CENTER_ARM_TARGETS = _arm_only(OBSERVE_CENTER_TARGETS)
OBSERVE_RIGHT_ARM_TARGETS = _arm_only(OBSERVE_RIGHT_TARGETS)
SCAN_LEFT_BASE_TARGET = {"base": OBSERVE_LEFT_TARGETS["base"]}
SCAN_RIGHT_BASE_TARGET = {"base": OBSERVE_RIGHT_TARGETS["base"]}

RANDOM_HISTORICAL_TEST_TARGETS = {
    "base": 0.5,
    "shoulder": 1.10,
    "elbow": -0.4,
    "wrist": 0.3,
    "roll": 0.0,
    "hand": 1.0,
}

EXISTING_MOTION_INVENTORY = {
    "reference_dh": {
        "targets": REFERENCE_DH_TARGETS,
        "evidence": "historical_pose",
        "production_status": "BLOCKED",
        "notes": (
            "Shoulder 1.50 exceeds the verified production limit; "
            "hand 1.0 requires gripper-policy review."
        ),
    },
    "candle": {
        "targets": CANDLE_ARM_TARGETS,
        "gripper_evidence": CANDLE_GRIPPER_EVIDENCE,
        "gripper_resolution": "UNRESOLVED",
        "evidence": "historical_conflict_arm_pose_supported",
        "production_status": "ARM_TARGETS_ONLY",
        "notes": (
            "The arm targets agree at zero. Historical hand values 1.49 "
            "and 1.0 conflict, so Candle never infers or commands a hand target."
        ),
    },
    "ready": {
        "targets": READY_TARGETS,
        "arm_only_targets": READY_ARM_TARGETS,
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
        "notes": (
            "The arm-only form intentionally preserves roll and gripper; "
            "it is not an exact six-joint reproduction."
        ),
    },
    "observe_left": {
        "targets": OBSERVE_LEFT_TARGETS,
        "arm_only_targets": OBSERVE_LEFT_ARM_TARGETS,
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
    },
    "observe_center": {
        "targets": OBSERVE_CENTER_TARGETS,
        "arm_only_targets": OBSERVE_CENTER_ARM_TARGETS,
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
    },
    "observe_right": {
        "targets": OBSERVE_RIGHT_TARGETS,
        "arm_only_targets": OBSERVE_RIGHT_ARM_TARGETS,
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
    },
    "scan_left": {
        "stages": (READY_ARM_TARGETS, SCAN_LEFT_BASE_TARGET),
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
    },
    "scan_right": {
        "stages": (READY_ARM_TARGETS, SCAN_RIGHT_BASE_TARGET),
        "evidence": "physically_used_strong",
        "production_status": "ARM_ONLY_AVAILABLE",
    },
    "random_historical_test": {
        "targets": RANDOM_HISTORICAL_TEST_TARGETS,
        "evidence": "historical_test_pose",
        "production_status": "BLOCKED",
        "notes": (
            "Elbow -0.4 is outside the verified minimum -0.366; "
            "hand 1.0 requires gripper-policy review."
        ),
    },
}


__all__ = [
    "CANDLE_ARM_TARGETS",
    "CANDLE_GRIPPER_EVIDENCE",
    "EXISTING_MOTION_INVENTORY",
    "OBSERVE_CENTER_ARM_TARGETS",
    "OBSERVE_CENTER_TARGETS",
    "OBSERVE_LEFT_ARM_TARGETS",
    "OBSERVE_LEFT_TARGETS",
    "OBSERVE_RIGHT_ARM_TARGETS",
    "OBSERVE_RIGHT_TARGETS",
    "RANDOM_HISTORICAL_TEST_TARGETS",
    "READY_ARM_TARGETS",
    "READY_TARGETS",
    "REFERENCE_DH_TARGETS",
    "SCAN_LEFT_BASE_TARGET",
    "SCAN_RIGHT_BASE_TARGET",
]
