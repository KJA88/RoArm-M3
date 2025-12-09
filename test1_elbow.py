import time
import serial
import json
import math

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.5)

def send(cmd):
    data = json.dumps(cmd) + "\n"
    print("SEND:", data.strip())
    ser.write(data.encode("utf-8"))
    time.sleep(0.2)

# Stop telemetry spam
send({"T":105, "cmd":0})

print("Starting CORRECTED ELBOW sweep (J4)...")

for elbow_deg in range(-90, 91, 15):
    elbow_rad = elbow_deg * math.pi/180
    print(f" → Moving elbow (J4) to {elbow_deg}°")

    send({
        "T":102,
        "j1": 0.0,   # base
        "j2": 0.0,   # shoulder pitch
        "j3": 0.0,   # shoulder lift
        "j4": elbow_rad,  # <-- REAL elbow
        "j5": 0.0,
        "j6": 0.0
    })

    time.sleep(0.8)

ser.close()
