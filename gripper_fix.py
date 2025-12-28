import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print("Attempting to force-close the gripper...")

    # Method A: Direct joint 6 movement (try to move to '0' position)
    device.write(b'{"T": 101, "joint": 6, "rad": 0, "spd": 0.2}\n')
    time.sleep(2)

    # Method B: The standard 'Close' command
    device.write(b'{"T": 106, "cmd": 1}\n')
    time.sleep(2)

    print("If it still hasn't moved, look for a mechanical jam.")
    device.close()
except Exception as e:
    print(f"Error: {e}")
