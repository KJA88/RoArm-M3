import serial, json, time

PORT = '/dev/ttyUSB0'
BAUD = 115200

def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode('utf-8'))
    time.sleep(2.5)

try:
    device = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print("--- Starting Sequence ---")
    send(device, {"T": 100}) # Home
    send(device, {"T": 102, "x": 150, "y": 100, "z": 100, "t": 0}) # Move to pick
    send(device, {"T": 106, "cmd": 1}) # Close
    send(device, {"T": 102, "x": 150, "y": 100, "z": 200, "t": 0}) # Lift
    send(device, {"T": 102, "x": 200, "y": 200, "z": 100, "t": 0}) # Move to drop
    send(device, {"T": 106, "cmd": 0}) # Open
    send(device, {"T": 100}) # Home
    device.close()
    print("--- Done ---")
except Exception as e:
    print(f"Error: {e}")
