#!/usr/bin/env python3

import serial
import time
import json
import paho.mqtt.client as mqtt

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Starting pose (Candle)
base_angle = -3.10
joint2 = 0
joint3 = 0
joint4 = 0
joint5 = 0
joint6 = 3.17

STEP = 0.12
MIN_BASE = -3.14
MAX_BASE = 3.14

UPDATE_INTERVAL = 0.35
last_update = 0

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

print("Connected to RoArm")

# Enable torque
ser.write((json.dumps({"T":210,"cmd":1})+"\n").encode())


def move_arm():

    cmd = {
        "T":101,
        "joint":[base_angle, joint2, joint3, joint4, joint5, joint6]
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

    move_arm()

    last_update = now


client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost",1883,60)

client.loop_forever()
