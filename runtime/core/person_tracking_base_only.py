#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import serial
import json
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

BROKER = "raspi"
TOPIC = "robot/track"

FRAME_WIDTH = 640

MAX_BASE = 1.6
MIN_BASE = -1.6

GAIN = 0.7
SMOOTH = 0.2

current_base = 0.0

SHOULDER = 0
ELBOW = 1.57
WRIST = 0
ROLL = 0
HAND = 3.14

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

def send_pose(base):

    cmd = {
        "T":102,
        "base":base,
        "shoulder":SHOULDER,
        "elbow":ELBOW,
        "wrist":WRIST,
        "roll":ROLL,
        "hand":HAND,
        "spd":100,
        "acc":70
    }

    ser.write((json.dumps(cmd)+"\n").encode())

print("Torque ON")
ser.write((json.dumps({"T":210,"cmd":1})+"\n").encode())

time.sleep(1)

send_pose(current_base)

time.sleep(2)

def on_connect(client, userdata, flags, rc):

    print("MQTT connected")

    client.subscribe(TOPIC)


def on_message(client, userdata, msg):

    global current_base

    payload = msg.payload.decode()

    if payload == "none":
        return

    cx = float(payload)

    error = cx - (FRAME_WIDTH/2)

    target = -(error / (FRAME_WIDTH/2)) * MAX_BASE

    target = target * GAIN

    target = max(MIN_BASE, min(MAX_BASE, target))

    current_base = current_base + (target-current_base)*SMOOTH

    print("Target:", round(target,2), "Base:", round(current_base,2))

    send_pose(current_base)


client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER,1883,60)

client.loop_forever()
