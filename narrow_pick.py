import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

# Narrow range to prevent motor jams
GRIP_OPEN   = 0.2  
GRIP_CLOSED = 0.7  

def move(ser, joints, desc):
    print(f"Executing: {desc}")
    ser.write((json.dumps({"T": 101, "joint": 1, "rad": joints[0]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 2, "rad": joints[1]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 3, "rad": joints[2]}) + "\n").encode())
    time.sleep(2.5)

def gripper(ser, pos, desc):
    print(f"Gripper: {desc} (Value: {pos})")
    # Using T: 101 for Joint 6 is the most precise way
    ser.write((json.dumps({"T": 101, "joint": 6, "rad": pos}) + "\n").encode())
    time.sleep(1.5)

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    
    # Initialize
    move(device, [0, 0, 0], "Candle Pose")
    
    # 1. Test Opening
    gripper(device, GRIP_OPEN, "Opening slightly")
    
    # 2. Reach
    move(device, [0, 0.8, 1.1], "Reaching")
    
    # 3. Test Closing
    gripper(device, GRIP_CLOSED, "Closing slightly")
    
    # 4. Lift
    move(device, [0, 0, 0], "Lifting")
    
    # 5. Release
    gripper(device, GRIP_OPEN, "Releasing")

    device.close()
    print("--- Test Finished ---")
except Exception as e:
    print(f"Error: {e}")
