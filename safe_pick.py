import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

# SWAPPED LOGIC: If your close command was opening it, we reverse the values.
GRIP_OPEN   = 0.0  # Was closing, now opening
GRIP_CLOSED = 1.1  # Was opening, now closing (Adjust this if it squeezes too hard)

def move(ser, joints, desc):
    print(f"Executing: {desc}")
    ser.write((json.dumps({"T": 101, "joint": 1, "rad": joints[0]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 2, "rad": joints[1]}) + "\n").encode())
    ser.write((json.dumps({"T": 101, "joint": 3, "rad": joints[2]}) + "\n").encode())
    time.sleep(2.5)

def gripper(ser, pos, desc):
    print(f"Gripper: {desc} (Value: {pos})")
    ser.write((json.dumps({"T": 101, "joint": 6, "rad": pos}) + "\n").encode())
    time.sleep(1.5)

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    
    # 1. Start at Candle
    move(device, [0, 0, 0], "Candle Pose")
    
    # 2. OPEN the gripper first
    gripper(device, GRIP_OPEN, "Opening gripper")
    
    # 3. REACH for the object
    move(device, [0, 0.8, 1.1], "Reaching for object")
    
    # 4. CLOSE the gripper to grab
    gripper(device, GRIP_CLOSED, "Closing on object")
    
    # 5. LIFT up
    move(device, [0, 0, 0], "Lifting object")
    
    # 6. ROTATE to drop zone
    move(device, [-1.0, 0, 0], "Rotating to side")
    
    # 7. OPEN to drop the object
    gripper(device, GRIP_OPEN, "Releasing object")
    
    # 8. RESET to Candle
    move(device, [0, 0, 0], "Returning to Candle")

    device.close()
    print("--- Sequence Finished ---")
except Exception as e:
    print(f"Error: {e}")
