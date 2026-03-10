import json
import serial
import time
import sys

# THE CONSTANTS (The "Hidden" Lengths)
# These are what the solver uses internally. 
# L1=Base, L2=UpperArm, L3=Forearm
L_LENGTHS = "L1: ~121mm, L2: ~150mm, L3: ~160mm"

def run():
    try:
        s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)
        time.sleep(1)
        
        # Wake the solver and release motors so you can move them
        s.write(b'{"command":"torque_set","cmd":0}\n')
        s.write(b'{"command":"echo_on"}\n')
        
        print("\033[2J") # Clear Screen
        while True:
            s.write(b'{"command":"feedback_get"}\n')
            line = s.readline().decode('utf-8', errors='ignore').strip()
            
            if '{' in line and '}' in line:
                try:
                    raw = line[line.find('{'):line.rfind('}')+1]
                    data = json.loads(raw).get("result", [])
                    if len(data) >= 10:
                        sys.stdout.write("\033[H")
                        print("=== ROARM INTERNAL SOLVER MONITOR ===")
                        print(f"HARDCODED LENGTHS: {L_LENGTHS}")
                        print("-" * 40)
                        print(f"XYZ RESULT (SOLVER OUTPUT):")
                        print(f" X: {data[0]:.2f} mm")
                        print(f" Y: {data[1]:.2f} mm")
                        print(f" Z: {data[2]:.2f} mm")
                        print("-" * 40)
                        print(f"RADIAN SOURCE (ENCODER INPUT):")
                        print(f" J1-J3: {data[4]:.3f}, {data[5]:.3f}, {data[6]:.3f}")
                        print(f" J4-J6: {data[7]:.3f}, {data[8]:.3f}, {data[9]:.3f}")
                        print("-" * 40)
                        print("MOVE ARM MANUALLY TO SEE CALCULATION")
                except:
                    continue
            time.sleep(0.05)
    except KeyboardInterrupt:
        # Re-lock motors on exit
        s.write(b'{"command":"torque_set","cmd":1}\n')
        s.close()
        print("\nExiting and locking motors.")

if __name__ == "__main__":
    run()
