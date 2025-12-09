import serial, time, json, os

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
BAUD = 115200

def get_pose():
    s = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(0.2)

    # Enable reporting
    s.write(b'{"T":605,"cmd":1}\n')
    time.sleep(0.3)

    # Request joint data
    s.write(b'{"T":105}\n')
    time.sleep(0.5)

    data = s.read_all().decode(errors="ignore")
    s.close()

    # Parse rad values
    start = data.find('"b":')
    if start == -1:
        raise Exception("Bad response:\n" + data)

    fields = {}
    keys = ["b","s","e","t","r","g"]  # base, shoulder, elbow, tilt, rotate, gripper

    for k in keys:
        idx = data.find(f'"{k}":')
        if idx != -1:
            num = data[idx+len(k)+3:].split(",")[0]
            fields[k] = float(num)

    return fields


def main():

    print("TURNING TORQUE OFF — move arm into position...")

    # DIRECT torque-off command (no alias)
    os.system(
        'python3 -c "import serial; s=serial.Serial(\\"/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0\\",115200); '
        's.write(b\'{\\"T\\":210,\\"cmd\\":0}\\n\'); s.close()"'
    )

    input("Move arm. When ready, press ENTER to record...")

    pose = get_pose()

    name = input("Enter pose name: ").strip()
    if not name:
        print("No name entered.")
        return

    path = f"/home/kallen/RoArm/recorder/{name}.json"
    with open(path, "w") as f:
        json.dump(pose, f, indent=4)

    print(f"\nSaved pose '{name}' to {path}")
    print("Recorded radians:")
    print(pose)


if __name__ == "__main__":
    main()

