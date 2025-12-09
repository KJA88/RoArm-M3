import time
from arm import Arm   # your actual interface class

arm = Arm()

# Keep all non-elbow joints still
base = 0.0
shoulder = 0.0
wrist_pitch = 0.0
wrist_roll = 0.0
claw = 0.0   # adjust if your gripper needs a neutral command

# Sweep elbow from -90° to +90° in 15° steps
for elbow_deg in range(-90, 91, 15):
    elbow_rad = elbow_deg * 3.14159265 / 180
    print(f"Moving elbow to {elbow_deg} degrees")
    arm.move_joints(base, shoulder, elbow_rad, wrist_pitch, wrist_roll, claw)
    time.sleep(0.7)
