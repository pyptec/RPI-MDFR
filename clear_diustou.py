import serial
import time

PORT = "/dev/ttyS0"

ser = serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=8,
    parity=serial.PARITY_NONE,
    stopbits=1,
    timeout=1
)

time.sleep(0.2)

clear_cmd = bytes.fromhex(
    "0D 0A 0D 0A 0D 0A 0D 0A"
)

print("Enviando clear command...")
ser.reset_input_buffer()
ser.reset_output_buffer()
ser.write(clear_cmd)
ser.flush()

time.sleep(0.5)

respuesta = ser.read(64)

print("Respuesta:", respuesta.hex(" "))

ser.close()

print("Clear enviado.")