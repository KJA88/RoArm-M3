#!/usr/bin/env python3
"""
Gripper presets and safety clamp for RoArm.

Based on measured mapping:
  1.2 rad -> ~114° open
  1.6 rad ->  90°
  2.0 rad ->  65°
  2.4 rad ->  45°
  2.8 rad ->  20°
  3.0 rad ->  10°
  3.2 rad -> fully pinched closed
"""

# Hard safety minimum: do not go below this (stall region)
HAND_MIN_SAFE    = 1.2   # rad

# Named presets (tune as needed)
HAND_OPEN        = 1.6   # ~90° open
HAND_SEMI_OPEN   = 2.0   # ~65°
HAND_HALF        = 2.4   # ~45°
HAND_PINCH       = 2.8   # ~20°
HAND_CLOSED      = 3.0   # ~10° (firmly closed)
HAND_HARD_CLOSE  = 3.2   # fully pinched; avoid holding here for long


def clamp_safe(g: float) -> float:
    """
    Clamp a raw gripper command to be at least HAND_MIN_SAFE.
    (You can also clamp max here later if you want.)
    """
    if g < HAND_MIN_SAFE:
        return HAND_MIN_SAFE
    return g
