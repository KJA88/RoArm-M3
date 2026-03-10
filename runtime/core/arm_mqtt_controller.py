#!/usr/bin/env python3

import time
import json
import serial
import math
import paho.mqtt.client as mqtt

# =========================
# Serial Settings
# =========================

PORT = "/dev/ttyUSB0"
BAUD = 115200

# =========================
# Lissajous parameters
# =========================

CX, CY, CZ = 240.0, 0.0, 250.0
WIDTH  = 80.0
HEIGHT = 40.0
LENGTH = 50.0

STEPS = 200
DT = 0.03
GRIPPER_RAD = 3.0

# =========================
# Globals
# =========================

ser = None
running_motion = False

# =========================
# Serial helpers
# =========================

def send_json(msg):
    line = json.dumps(msg) + "\n"
    ser.write(line.encode("utf-8"))

# =========================
# Motion routine
# =========================

def run_lissajous():

    global running_motion

    if running_motion:
        return

    running_motion = True

    print("Starting Lissajous motion")

    send_json({"T":210,"cmd":1})
    time.sleep(0.5)

    send_json({
        "T":104,
        "x":CX,"y":CY,"z":CZ,
        "t":0,"r":0,"g":GRIPPER_RAD,"spd":0.5
    })

    time.sleep(2)

    for i in range(STEPS):

        phi = 2*math.pi*(i/STEPS)

        tx = CX + (LENGTH/2)*math.cos(phi)
        ty = CY + WIDTH*math.sin(2*phi)
        tz = CZ + HEIGHT*math.sin(phi)

        tt = 0.3*math.cos(phi)

        send_json({
            "T":1041,
            "x":round(tx,2),
            "y":round(ty,2),
            "z":round(tz,2),
            "t":round(tt,2),
            "r":0,
            "g":GRIPPER_RAD
        })

        time.sleep(DT)

    print("Returning to candle")

    send_json({
        "T":104,
        "x":0,"y":0,"z":400,
        "t":0,"r":0,"g":GRIPPER_RAD,"spd":0.5
    })

    running_motion = False


# =========================
# MQTT callbacks
# =========================

def on_connect(client, userdata, flags, rc):
    print("MQTT connected")
    client.subscribe("robot/vision")

def on_message(client, userdata, msg):

    message = msg.payload.decode()
    print("Received:", message)

    if message == "person":
        run_lissajous()

# =========================
# Main
# =========================

def main():

    global ser

    print("Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("localhost",1883,60)

    client.loop_forever()


if __name__ == "__main__":
    main()