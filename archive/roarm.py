import serial, time, re

# Open serial port to RoArm
s = serial.Serial("/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0", 115200, timeout=1)
s.setRTS(False)
s.setDTR(False)

print("\nRoArm READY — type JSON commands (Ctrl+C to quit)\n")

# Safe home pose (shoulder up, elbow 90°, gripper closed)
SAFE_HOME = '{"T":101,"cmd":0} {"T":102,"cmd":0} {"T":103,"cmd":1.57} {"T":106,"cmd":0}'

while True:
    try:
        cmd = input(">>> ")

        # Custom safe home command
        if cmd.strip().lower() == "home":
            cmds = SAFE_HOME.split()
            for c in cmds:
                s.write((c + "\n").encode())
                time.sleep(0.2)
            continue

        # Clamp shoulder (102) and elbow (103) to safe ranges
        joint_match = re.search(r'"T":(102|103).*?cmd":([\-0-9\.]+)', cmd)
        if joint_match:
            joint = int(joint_match.group(1))
            val = float(joint_match.group(2))

            if joint == 102:    # Shoulder safe range
                if val > 0.7: val = 0.7
                if val < -0.8: val = -0.8

            if joint == 103:    # Elbow safe range
                if val > 1.3: val = 1.3
                if val < -1.3: val = -1.3

            cmd = f'{{"T":{joint},"cmd":{val}}}'

        # Send command to arm
        s.write((cmd + "\n").encode())

    except KeyboardInterrupt:
        print("\nExiting RoArm controller.")
        break

s.close()
