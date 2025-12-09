import serial
import time
import json

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"

with serial.Serial(PORT, 115200, timeout=1) as s:
    s.reset_input_buffer()

    # Request joint + Cartesian feedback
    s.write(b'{"T":105}\n')
    time.sleep(0.4)

    # Try up to 50 lines to find valid JSON
    for _ in range(50):
        raw = s.readline().decode("utf-8", errors="ignore").strip()

        # Skip empty or invalid lines
        if not raw:
            continue
        if raw[0] != "{" or raw[-1] != "}":
            continue

        try:
            data = json.loads(raw)
        except:
            continue

        # ---- POSITION ----
        print("\n=== POSITION ===")
        print(f"  x: {data['x']:8.1f} mm")
        print(f"  y: {data['y']:8.1f} mm")
        print(f"  z: {data['z']:8.1f} mm")
        print(f"pitch(tit): {data.get('tit', 0):6.3f} rad")

        # ---- JOINT ANGLES ----
        print("\n=== JOINT ANGLES ===")
        print(f"  base (b):     {data['b']:6.3f} rad")
        print(f"  shoulder (s): {data['s']:6.3f} rad")
        print(f"  elbow (e):    {data['e']:6.3f} rad")
        print(f"  wrist (t):    {data['t']:6.3f} rad")
        print(f"  roll (r):     {data['r']:6.3f} rad")
        print(f"  gripper (g):  {data['g']:6.3f} rad")

        # ---- MOTOR LOADS ----
        print("\n=== MOTOR LOADS ===")
        print(f"  Base  tB: {data['tB']}")
        print(f"  Shld  tS: {data['tS']}")
        print(f"  Elbw  tE: {data['tE']}")
        print(f"  Wrist tT: {data['tT']}")
        print(f"  Roll  tR: {data['tR']}")
        break

    else:
        print("⚠ No valid JSON received from robot!")
