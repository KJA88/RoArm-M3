#!/usr/bin/env python3
import argparse
import json
import time
import serial

def send_cmd(ser, cmd_dict):
    msg = json.dumps(cmd_dict) + "\n"
    ser.write(msg.encode('utf-8'))
    print(f"→ Sent: {msg.strip()}")

def main():
    parser = argparse.ArgumentParser()
    # Adding subparsers back so your 'rogo' alias works
    subparsers = parser.add_subparsers(dest="command")
    goto_parser = subparsers.add_parser('goto_xyz')
    
    # Coordinates
    goto_parser.add_argument('x', type=float)
    goto_parser.add_argument('y', type=float)
    goto_parser.add_argument('z', type=float)
    
    # Options
    parser.add_argument('--port', default='/dev/ttyUSB0')
    parser.add_argument('--spd', type=int, default=100)
    parser.add_argument('--acc', type=int, default=50)
    
    args = parser.parse_args()

    try:
        # Standard Waveshare Setup [cite: 31, 35]
        ser = serial.Serial(args.port, baudrate=115200, timeout=1, dsrdtr=None)
        ser.setRTS(False)
        ser.setDTR(False)
        time.sleep(0.3)

        # 1. Torque ON (CMD_TORQUE_CTRL) 
        send_cmd(ser, {"T": 210, "cmd": 1})
        time.sleep(0.1)

        # 2. Move using the Wiki's IK format (T:102) 
        # Firmware handles the IK solution internally [cite: 66]
        move_cmd = {
            "T": 102,
            "x": args.x,
            "y": args.y,
            "z": args.z,
            "spd": args.spd,
            "acc": args.acc
        }
        
        send_cmd(ser, move_cmd)

        # 3. Get Feedback (T:105) [cite: 37, 46]
        time.sleep(2.0)
        send_cmd(ser, {"T": 105})
        fb = ser.readline().decode('utf-8', errors='ignore').strip()
        print(f"Arm Feedback: {fb}")

        ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
