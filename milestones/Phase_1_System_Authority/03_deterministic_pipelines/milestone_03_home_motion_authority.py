"""Compatibility wrapper for the opaque legacy home action."""
from runtime.core.safety.production_motion import deny_unsupported


def arm_home():
    return {
        "armed": False,
        "reason": "HOME_POLICY_UNVERIFIED",
        "sha256": None,
    }


def execute_home():
    return deny_unsupported("home", reason="HOME_POLICY_UNVERIFIED")
