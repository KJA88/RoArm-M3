#!/usr/bin/env python3
import serial, time

PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"

s = serial.Serial(PORT, 115200, timeout=1)
s.setRTS(False)
s.setDTR(False)

s.write(b'{"T":210,"hold":1}\n')
time.sleep(0.2)

print("Torque ON sent (T=210, hold=1).")
s.close()
