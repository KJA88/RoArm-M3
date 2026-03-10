#!/usr/bin/env python3

import serial
import time
import json
import paho.mqtt.client as mqtt

PORT = "/dev/ttyUSB0"
BAUD = 115200

# base rotation state
base_angle = 0.0

# movement step
STEP = 0.08

# workspace pose
X = 240
Y = 0
Z = 250

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

print("Serial connected to arm")


def send_pose():

    cmd = {
        "T":104,
        "x":X,
        "y":Y,
        "z":Z,
        "t":base_angle,
        "r":0,
        "g":3,
        "spd":0.4
    }

    ser.write((json.dumps(cmd) + "\n").encode())


def on_connect(client, userdata, flags, rc):
    print("MQTT connected")
    client.subscribe("robot/track")


def on_message(client, userdata, msg):

    global base_angle

    direction = msg.payload.decode()

    print("Tracking:", direction)

    if direction == "left":
        base_angle += STEP

    elif direction == "right":
        base_angle -= STEP

    elif direction == "center":
        return

    send_pose()


client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

client.loop_forever()
