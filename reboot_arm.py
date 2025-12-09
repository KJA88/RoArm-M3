#!/usr/bin/env python3
import serial, time

s = serial.Serial("/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0",115200,timeout=1)
s.setDTR(False)
s.setRTS(False)

# system reset
s.write(b'{"T":999}\n')
time.sleep(1.0)

print("Sent T=999 (system reboot). Power cycle if no movement.")
s.close()
