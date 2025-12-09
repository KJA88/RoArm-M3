import serial, time, json, sys

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
BAUD = 115200

def move_joint(joint, rad, spd=40, acc=40):
    return f'{{"T":101,"joint":{joint},"rad":{rad},"spd":{spd},"acc":{acc}}}\n'.encode()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 play_preset.py <pose>")
        return

    pose_name = sys.argv[1]
    path = f"/home/kallen/RoArm/recorder/{pose_name}.json"

    try:
        pose = json.load(open(path))
    except:
        print(f"Pose '{pose_name}' not found at: {path}")
        return

    # Mapping rad names to actual joint numbers
    joint_map = {
        "b": 1,  # base
        "s": 2,  # shoulder
        "e": 3,  # elbow
        "t": 4,  # tilt
        "r": 5,  # rotate
        "g": 6,  # gripper
    }

    print(f"Moving to pose: {pose_name}")

    s = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(0.2)

    for key, rad in pose.items():
        joint = joint_map[key]
        s.write(move_joint(joint, rad))
        time.sleep(0.05)

    s.close()
    print("Done.")

if __name__ == "__main__":
    main()
