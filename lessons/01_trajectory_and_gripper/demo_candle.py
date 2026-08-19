#!/usr/bin/env python3

import json
import time
import serial

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
BAUD = 115200


def send(ser, obj):
    ser.write((json.dumps(obj) + "\n").encode("utf-8"))
    ser.flush()


def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    ser.setRTS(False)
    ser.setDTR(False)
    time.sleep(0.2)

    # Enable torque before commanded movement.
    send(ser, {"T": 210, "cmd": 1})
    time.sleep(0.5)

    # Physically verified joint-space Candle arm pose.
    #
    # IMPORTANT:
    # Gripper/hand is intentionally NOT commanded here.
    # Named arm poses must not silently open, close, or otherwise
    # change the gripper. Gripper motion is controlled separately
    # through the dedicated named-gripper authority.
    send(
        ser,
        {
            "T": 102,
            "base": 0,
            "shoulder": 0,
            "elbow": 0,
            "wrist": 0,
            "roll": 0,
            "spd": 0,
            "acc": 0,
        },
    )

    time.sleep(2.0)
    ser.close()

    print("Candle arm pose command completed. Gripper unchanged.")


if __name__ == "__main__":
    main()
