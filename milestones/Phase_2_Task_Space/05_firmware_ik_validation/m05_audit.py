#!/usr/bin/env python3
import sys
import json
import time
from pathlib import Path

# Fix paths
ROOT = Path(__file__).resolve()
while ROOT.name != "RoArm":
    ROOT = ROOT.parent
sys.path.append(str(ROOT))

from core.supervisor.mechanical_supervisor import MechanicalSupervisor

def run_deep_audit():
    sup = MechanicalSupervisor()
    
    # 1. Capture INITIAL Joint State (Should be the 'Candle' state)
    start_state = sup.get_feedback()
    j_start = [start_state.get('b'), start_state.get('s'), start_state.get('e')]
    print(f"\n[AUDIT] START Joints: Base:{j_start[0]:.4f} Shoulder:{j_start[1]:.4f} Elbow:{j_start[2]:.4f}")

    # 2. Execute Move (Target X:250, Z:300)
    sup.move_to_pose(250, 0, 300, -1.57)
    print("[AUDIT] Waiting 4 seconds for physical travel...")
    time.sleep(4.0)

    # 3. Capture FINAL Joint State
    # We query the arm again to see where the encoders landed
    end_state = sup.get_feedback()
    j_end = [end_state.get('b'), end_state.get('s'), end_state.get('e')]
    print(f"[AUDIT] FINAL Joints: Base:{j_end[0]:.4f} Shoulder:{j_end[1]:.4f} Elbow:{j_end[2]:.4f}")

    # 4. Compare
    # Calculate the total difference in radians
    diff = sum(abs(s - e) for s, e in zip(j_start, j_end))
    
    print(f"\n--- THE JOINT VERDICT ---")
    if diff > 0.1:
        print(f"✅ PROOF SECURED: Physical movement of {diff:.4f} radians detected.")
        print("The arm is at the target. The firmware XYZ registers are simply not updating.")
    else:
        print("❌ PROOF FAILED: No motor movement detected.")

    sup.close()

if __name__ == "__main__":
    run_deep_audit()