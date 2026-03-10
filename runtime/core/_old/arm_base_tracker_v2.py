#!/usr/bin/env python3

import serial
import time
import json
import paho.mqtt.client as mqtt

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Base joint position (radians)
base_angle = 0.0

# Rotation step per update
STEP = 0.12

# Limits to prevent over-rotation
MIN_BASE = -3.0
MAX_BASE = 3.0

# Timing limit so we don't spam the arm
UPDATE_INTERVAL = 0.4
last_update = 0

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

print("Connected to RoArm")

# Enable torque
ser.write((json.dumps({"T":210,"cmd":1})+"\n").encode())

def move_base(angle):

    cmd = {
        "T":101,
        "joint":[angle, None, None, None, None, None]
    }

    ser.write((json.dumps(cmd)+"\n").encode())


def on_connect(client, userdata, flags, rc):
    print("MQTT connected")
    client.subscribe("robot/track")


def on_message(client, userdata, msg):

    global base_angle, last_update

    direction = msg.payload.decode()

    now = time.time()
    if now - last_update < UPDATE_INTERVAL:
        return

    if direction == "left":
        base_angle += STEP

    elif direction == "right":
        base_angle -= STEP

    elif direction == "center":
        return

    base_angle = max(MIN_BASE, min(MAX_BASE, base_angle))

    print("Base angle:", round(base_angle,2))

    move_base(base_angle)

    last_update = now


client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost",1883,60)

client.loop_forever()
