import sys
from pathlib import Path

# Adjusting path to find 'core' from two sub-directory levels deep
# milestones -> Phase_1_System_Authority -> 03_deterministic_pipelines
sys.path.append(str(Path(__file__).resolve().parents[3]))

try:
    from core.supervisor.mechanical_supervisor import MechanicalSupervisor
except ImportError as e:
    print(f"CRITICAL: Could not find MechanicalSupervisor. Check folder structure. Error: {e}")
    sys.exit(1)

# 1. Initialize & Safety Check
# This triggers the prompt to confirm the arm is in the Candle position
sup = MechanicalSupervisor()

# 2. The Milestone Test Move (Shoulder to 0.4 rad)
print("\n--- STAGE 1: MOVING TO TEST POSITION ---")
sup.move_joint(2, 0.4)

# 3. Auto-Home and Torque-Off
# This returns the arm to 0.0 before exiting
print("\n--- STAGE 2: CLEANUP & HOMING ---")
sup.close()
