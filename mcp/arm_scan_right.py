#!/usr/bin/env python3
import sys
from pathlib import Path

AUTH_DIR = Path("/home/KA_PI/robotics/roarm-m3/milestones/Phase_1_System_Authority/03_deterministic_pipelines")
sys.path.insert(0, str(AUTH_DIR))

from milestone_03_scan_right_motion_authority import arm_scan_right

permit = arm_scan_right()

print()
print("RoArm SCAN RIGHT motion ARMED")
print("Authority: LOCAL OPERATOR / ONE USE")
print("Expires: 120 seconds")
print("Authority SHA-256:", permit["sha256"])
print()
print("The next authorized Scan Right call may execute physical motion.")
