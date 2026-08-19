#!/usr/bin/env python3

import sys
from pathlib import Path

AUTH_DIR = Path(
    "/home/KA_PI/robotics/roarm-m3/"
    "milestones/Phase_1_System_Authority/"
    "03_deterministic_pipelines"
)

sys.path.insert(0, str(AUTH_DIR))

from milestone_03_joint_motion_authority import (
    arm_constrained_joint_motion,
)

permit = arm_constrained_joint_motion()

print()
print("RoArm constrained joint motion ARMED")
print("Authority: LOCAL OPERATOR / ONE USE")
print("Scope: ONE shoulder/elbow/wrist target")
print("Expires: 120 seconds")
print("Authority SHA-256:", permit["sha256"])
print()
print(
    "The next valid move_constrained_joint call may execute "
    "one physical joint movement."
)
