#!/usr/bin/env python3
import serial
import time

PORT = "/dev/ttyUSB5"

cmd = bytes.fromhex("01 03 00 00 00 01 84 0A")

print("Abriendo puerto:", PORT)

ser = serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=8,
    parity='E',
    stopbits=1,
    timeout=2
)

ser.reset_input_buffer()
ser.reset_output_buffer()

print("TX:", cmd.hex(" ").upper())

ser.write(cmd)

time.sleep(1)

rx = ser.read(100)

if rx:
    print("RX:", rx.hex(" ").upper())
else:
    print("SIN RESPUESTA")

ser.close()