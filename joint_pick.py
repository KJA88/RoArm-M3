import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

def move(ser, joints, desc):
    # T: 101 moves specific joints (Base, Shoulder, Elbow, Wrist, Hand, etc.)
    # The list is typically [J1, J2, J3, J4, J5, J6] in radians or degrees
    print(f"Executing: {desc}")
    cmd = {"T": 101, "joint": joints[0], "rad": joints[1], "spd": 0.5, "acc": 0.1}
    # Some M3 versions use a list format: {"T": 101, "p": joints, "s": 0.5, "a": 0.1}
    # We will send the standard individual joint command for J1-J6
    ser.write((json.dumps({"T": 101, "joint": 1, "rad": joints[0]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 2, "rad": joints[1]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 3, "rad": joints[2]}) + "\n").encode())
    time.sleep(3)

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    
    print("--- Starting Joint Sequence ---")
    
    # 1. CANDLE POSITION (All joints at 0 or vertical)
    move(device, [0, 0, 0], "Moving to Candle")
    
    # 2. REACH FORWARD (Shoulder and Elbow adjust)
    # Values are in Radians. 1.57 is roughly 90 degrees.
    move(device, [0, 0.8, 1.2], "Reaching for object")
    
    # 3. GRAB (Joint 6 is usually the hand)
    print("Action: Closing Gripper")
    device.write(b'{"T": 106, "cmd": 1}\n')
    time.sleep(2)
    
    # 4. LIFT (Back to Candle while holding)
    move(device, [0, 0, 0], "Lifting object")
    
    # 5. ROTATE BASE
    move(device, [1.0, 0, 0], "Rotating to side")
    
    # 6. RELEASE
    print("Action: Opening Gripper")
    device.write(b'{"T": 106, "cmd": 0}\n')
    time.sleep(2)

    device.close()
    print("--- Done ---")
except Exception as e:
    print(f"Error: {e}")
