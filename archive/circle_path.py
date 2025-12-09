#!/usr/bin/env python3
import numpy as np
import time
import serial
import json

# --- CONFIGURATION ---
PORT = '/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0'

# Maximum allowable speed for the T:123 command (e.g., 0.5 rad/s or 0.5 unit/s)
# The servo firmware typically accepts a range like 1 to 10 for speed scaling.
MAX_SPEED_SCALE = 5 

def send(cmd_dict):
    """Sends a JSON command dictionary to the robot."""
    cmd_str = json.dumps(cmd_dict)
    print(f"Sending: {cmd_str}") # Print command for debugging
    try:
        with serial.Serial(PORT, 115200, timeout=1) as s:
            s.write((cmd_str + "\n").encode('utf-8'))
    except serial.SerialException as e:
        print(f"Error connecting to port: {e}")

# Continuous velocity command for a single axis (J1-J6)
def vel_joint(joint_axis, value):
    """
    Commands continuous velocity for a joint.
    joint_axis: 1=Base, 2=Shoulder, 3=Elbow, etc.
    value: float from -1.0 to +1.0 (relative speed scale)
    """
    # 1. Determine Direction: 1=Forward/Increase, 2=Backward/Decrease
    if value >= 0:
        direction = 1 
    else:
        direction = 2 

    # 2. Scale Speed: Convert the relative value to the absolute speed scale (1 to MAX_SPEED_SCALE)
    # The firmware expects a positive speed value.
    speed = abs(value) * MAX_SPEED_SCALE
    
    # 3. Build Command: T:123, m:1 (Continuous mode), axis: Joint number
    cmd = {
        "T": 123,
        "m": 1,
        "axis": joint_axis,
        "cmd": direction,
        "spd": speed
    }
    send(cmd)

# Stop continuous movement on a joint axis
def stop_joint(joint_axis):
    """Stops continuous movement on the specified joint axis (cmd: 0)."""
    cmd = {
        "T": 123,
        "m": 1,
        "axis": joint_axis,
        "cmd": 0
    }
    send(cmd)

def draw_circle(duration=5.0, radius=0.5):
    """
    Draws a circle in the J2 (Shoulder) and J3 (Elbow) space.
    Note: This draws a circle in joint space, not XYZ world space!
    """
    steps = 400
    dt = duration / steps
    
    print(f"Starting circle drawing for {duration} seconds...")

    for i in range(steps):
        theta = 2 * np.pi * (i / steps)

        # Velocity components for a circle path in J2/J3 space
        # J2 (Shoulder) velocity: vx = -sin(theta) (for smooth start/stop)
        # J3 (Elbow) velocity: vy = cos(theta)
        
        # Scaling by 'radius' controls the speed/aggressiveness of the circle
        v_shoulder = -np.sin(theta) * radius 
        v_elbow = np.cos(theta) * radius 

        # Joint 2 = Shoulder, Joint 3 = Elbow
        vel_joint(2, v_shoulder) 
        vel_joint(3, v_elbow) 

        time.sleep(dt)

    # Stop movement
    print("Stopping movement...")
    stop_joint(2)
    stop_joint(3)

if __name__ == "__main__":
    # Ensure the virtual environment is active before running.
    draw_circle(duration=6.0, radius=0.5)
    print("Done.")
