import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

def send(ser, cmd, desc):
    print(f"Action: {desc}")
    ser.write((json.dumps(cmd) + "\n").encode('utf-8'))
    time.sleep(2.5)

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    
    # 1. TORQUE ON (Command 210 from your Wiki doc)
    send(device, {"T": 210, "cmd": 1}, "Engaging Motors")

    # 2. MOVE TO START (Using T: 101 for Joints)
    # Joints: 1=Base, 2=Shoulder, 3=Elbow, 4=Wrist, 5=Roll, 6=Gripper
    # We move them to a "Ready" position
    print("Moving to Ready Pose...")
    send(device, {"T": 101, "joint": 1, "rad": 0}, "Base Center")
    send(device, {"T": 101, "joint": 2, "rad": 0.5}, "Shoulder Forward")
    send(device, {"T": 101, "joint": 3, "rad": 0.8}, "Elbow Down")

    # 3. OPEN GRIPPER (Joint 6)
    # If it opens too far, we use a small radian value like 0.5
    send(device, {"T": 101, "joint": 6, "rad": 0.5}, "Opening Gripper Safely")

    # 4. CLOSE GRIPPER (To grab)
    # Usually, 2.0 or 3.14 is "Closed" in this firmware
    send(device, {"T": 101, "joint": 6, "rad": 2.0}, "Closing Gripper")

    # 5. LIFT
    send(device, {"T": 101, "joint": 2, "rad": 0.0}, "Lifting (Shoulder Up)")

    # 6. RESET
    print("Sequence Complete.")
    device.close()

except Exception as e:
    print(f"Error: {e}")
