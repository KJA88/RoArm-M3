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
        "hand":     float(rad[5]), # <-- J6 Gripper is sent here
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


def move_to(x, y, z, r, g): # <-- NOW ACCEPTS 'G' (Gripper)
    global LAST_JOINTS_5DOF 

    target_xyz = np.array([x, y, z], dtype=float)
    target_roll = r
    print(f"\n>>> IK target XYZ = {target_xyz}, Target Roll (rad) = {target_roll}, Target Gripper (rad) = {g}")

    # Use the last successful solution as the initial guess (Warm Start)
    initial_guess = LAST_JOINTS_5DOF
    
    # Calculate J1-J5 using IK
    joints_5dof = inverse_kinematics(target_xyz, target_roll, initial_guess) 
    
    if joints_5dof is None:
        print("Move failed: IK did not find a valid solution.")
        return

    # Store the first 5 joints of the successful solution for the next warm start
    LAST_JOINTS_5DOF = joints_5dof[0:5] 
    
    # Build the full 6-DoF joint vector: [J1, J2, J3, J4, J5, J6]
    full_joints_6dof = np.array([
        joints_5dof[0],
        joints_5dof[1],
        joints_5dof[2],
        joints_5dof[3],
        joints_5dof[4],
        g # <-- Insert the commanded Gripper angle (J6) here
    ])
    
    print("IK joints solution (J1-J6):", full_joints_6dof)

    xyz_check, _ = forward_kinematics(full_joints_6dof)
    print("FK check (where the arm will actually go):", xyz_check)
    print(f"J5 Roll commanded: {full_joints_6dof[4]:.3f} rad, J6 Gripper commanded: {g:.3f} rad")

    # SAFETY CHECK
    if z < 50.0:
        print("⚠️ WARNING: Target Z is low. Proceeding slowly.")
        time.sleep(1)

    send_joints(full_joints_6dof)

def main():
    # NOW REQUIRES 7 arguments: script, command, X, Y, Z, R, G
    if len(sys.argv) != 7:
        print("Usage: python3 roarm_control.py move X Y Z R G")
        print("\nNote: G is the desired Gripper angle in radians (e.g., 0.0 for open, ~3.0 for closed).")
        sys.exit(1)

    _, cmd, xs, ys, zs, rs, gs = sys.argv # <-- NOW EXTRACTS 'gs'
    if cmd != "move":
        print("Only 'move' command supported.")
        sys.exit(1)

    try:
        x = float(xs)
        y = float(ys)
        z = float(zs)
        r = float(rs) 
        g = float(gs) # <-- CONVERTS 'gs' TO FLOAT 'g'
    except ValueError:
        print("X, Y, Z, R, and G must be valid numbers.")
        sys.exit(1)

    move_to(x, y, z, r, g) # <-- PASSES 'g' TO move_to

if __name__ == "__main__":
    main()
