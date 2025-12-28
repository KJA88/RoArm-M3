import json
import time
import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.2)
time.sleep(0.5)

# --- IMPORTANT: clear any old junk ---
ser.reset_input_buffer()

def get_xyz():
    ser.write(b'{"T":105}\n')
    t0 = time.time()
    while time.time() - t0 < 2.0:
        line = ser.readline()
        if not line:
            continue
        try:
            msg = json.loads(line.decode(errors="ignore"))
        except json.JSONDecodeError:
            continue

        if isinstance(msg, dict) and msg.get("T") == 1051:
            return msg["x"], msg["y"], msg["z"]

    raise RuntimeError("No valid T=1051 feedback received")

# --- STEP 1: read current pose ---
x, y, z = get_xyz()
print("Current pose:", x, y, z)

# --- STEP 2: send a SMALL, OBVIOUS XY MOVE ---
target = {
    "T": 104,
    "x": x + 30,   # 30 mm in X (visible)
    "y": y,
    "z": z
}

print("Sending command:", target)
ser.write(json.dumps(target).encode() + b"\n")

ser.close()
