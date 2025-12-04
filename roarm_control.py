#!/usr/bin/env python3
import sys
import json
import serial
import numpy as np
import time 

from ik import inverse_kinematics
from fk import forward_kinematics

# Verify the port is correct for your setup
PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"

# GLOBAL STATE: Stores the last successful joint solution (J1-J5) for warm-start IK.
# Initialized to a safe, common start pose.
LAST_JOINTS_5DOF = np.array([0.0, 0.5, 0.5, 0.0, 0.0], dtype=float) 

def send_joints(rad):
    """
    rad: [J1..J6] in radians
    Sends T=102 command.
    """
    cmd = {
        "T": 102,
        "base":     float(rad[0]),
        "shoulder": float(rad[1]),
        "elbow":    float(rad[2]),
        "wrist":    float(rad[3]),
        "roll":     float(rad[4]),
        "hand":     float(rad[5]),
        "spd": 0, 
        "acc": 0
    }

    print("Sending:", cmd)

    try:
        with serial.Serial(PORT, 115200, timeout=1) as s:
            s.write((json.dumps(cmd) + "\n").encode("utf-8"))
            s.flush()
    except serial.SerialException as e:
        print(f"ERROR: Could not open serial port {PORT}. Is the arm connected and authorized? {e}")


def move_to(x, y, z, r):
    global LAST_JOINTS_5DOF # Declare to modify the global variable

    target_xyz = np.array([x, y, z], dtype=float)
    target_roll = r
    print(f"\n>>> IK target XYZ = {target_xyz}, Target Roll (rad) = {target_roll}")

    # Use the last successful solution as the initial guess (Warm Start)
    initial_guess = LAST_JOINTS_5DOF
    
    # Pass the initial guess to the IK solver
    joints = inverse_kinematics(target_xyz, target_roll, initial_guess) 
    
    if joints is None:
        print("Move failed: IK did not find a valid solution.")
        return

    print("IK joints solution:", joints)

    # Store the first 5 joints of the successful solution for the next warm start
    # We only store J1-J5, as J6 is the gripper and is fixed at 0.0 in IK.
    LAST_JOINTS_5DOF = joints[0:5] 
    
    xyz_check, _ = forward_kinematics(joints)
    print("FK check (where the arm will actually go):", xyz_check)
    print(f"J5 Roll commanded: {joints[4]:.3f} rad")

    # SAFETY CHECK
    if z < 50.0:
        print("⚠️ WARNING: Target Z is low. Proceeding slowly.")
        time.sleep(1)

    send_joints(joints)

def main():
    # NOW REQUIRES 6 arguments: script, command, X, Y, Z, R
    if len(sys.argv) != 6:
        print("Usage: python3 roarm_control.py move X Y Z R")
        print("\nNote: R is the desired Wrist Roll angle in radians (e.g., 0.0 or 1.57)")
        sys.exit(1)

    _, cmd, xs, ys, zs, rs = sys.argv 
    if cmd != "move":
        print("Only 'move' command supported.")
        sys.exit(1)

    try:
        x = float(xs)
        y = float(ys)
        z = float(zs)
        r = float(rs) 
    except ValueError:
        print("X, Y, Z, and R must be valid numbers.")
        sys.exit(1)

    move_to(x, y, z, r) 

if __name__ == "__main__":
    main()
