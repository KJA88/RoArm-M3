import serial
import time

# Open serial connection
s = serial.Serial('/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0', 115200, timeout=2)

# Enable telemetry
s.write(b'{\"T\":605,\"cmd\":1}\\n')
time.sleep(0.5)

# Ask for current joint angles
s.write(b'{\"T\":105}\\n')
time.sleep(1.0)

# Read and print the response
data = s.readline().decode(errors="ignore").strip()

if data:
    print("Captured Pose:", data)
else:
    print("⚠️ No response after enabling telemetry and sending T:105.")

s.close()
