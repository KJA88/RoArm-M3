# roarm_safety.py
#
# Minimal safety helper for RoArm.
# Right now:
#   - Ensures hand (gripper) angle never goes below HAND_MIN.
#   - Provides a JointState dataclass we can reuse later.

from dataclasses import dataclass

# ---- SAFETY CONSTANTS (TUNE LATER) ----
HAND_MIN = 1.1  # rad; gripper should never go below this (stall risk)


@dataclass
class JointState:
    base: float
    shoulder: float
    elbow: float
    wrist: float
    roll: float
    hand: float


def clamp_hand(q: JointState) -> JointState:
    """
    Return a copy of q where hand is clamped to at least HAND_MIN.
    """
    hand = q.hand
    if hand < HAND_MIN:
        hand = HAND_MIN

    return JointState(
        base=q.base,
        shoulder=q.shoulder,
        elbow=q.elbow,
        wrist=q.wrist,
        roll=q.roll,
        hand=hand,
    )
