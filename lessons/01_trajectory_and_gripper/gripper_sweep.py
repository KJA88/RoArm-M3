#!/usr/bin/env python3
import serial, time, json

PORT = "/dev/ttyUSB0"
BAUD = 115200

# List of gripper commands (radians) you want to test
G_VALUES = [1.2, 1.6, 2.0, 2.4, 2.8, 3.0, 3.2]

def send(ser, cmd):
    ser.write((json.dumps(cmd) + "\n").encode("ascii"))

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    time.sleep(0.3)

    # Torque ON
    send(ser, {"T": 210, "cmd": 1})
    time.sleep(0.3)

    print("Starting gripper sweep. For each value, measure the angle and write it down.")
    input("Position arm safely, then press ENTER to begin...")

    for g in G_VALUES:
        print(f"\nCommanding gripper g = {g:.3f} rad")
        cmd = {
            "T": 102,
            "base": 0.0,
            "shoulder": 1.5,
            "elbow": 0.0,
            "wrist": 0.0,
            "roll": 0.0,
            "hand": g,
            "spd": 0,
            "acc": 0,
        }
        send(ser, cmd)
        time.sleep(1.0)  # wait to settle

        # Ask firmware for feedback (optional)
        send(ser, {"T": 105})
        time.sleep(0.1)
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print("Feedback line:", line)

        input(f"Measure the physical gripper angle for g={g:.3f}. Write it down, then press ENTER.")

    print("\nSweep complete. Turning torque OFF.")
    send(ser, {"T": 210, "cmd": 0})
    time.sleep(0.2)

    ser.close()

if __name__ == "__main__":
    main()
