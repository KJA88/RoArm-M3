from roarm_sdk.roarm import roarm

arm = roarm(
    roarm_type="roarm_m3",
    port="/dev/ttyUSB0",
    baudrate=115200
)

print("POSE:")
print(arm.pose_get())

print("\nJOINT ANGLES:")
print(arm.joints_angle_get())
