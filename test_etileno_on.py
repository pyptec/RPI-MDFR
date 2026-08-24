import minimalmodbus
import serial

PORT = "/dev/ttyS0"
SLAVE = 2

instrument = minimalmodbus.Instrument(PORT, SLAVE)
instrument.serial.baudrate = 9600
instrument.serial.bytesize = 8
instrument.serial.parity = serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout = 1
instrument.mode = minimalmodbus.MODE_RTU
instrument.clear_buffers_before_each_transaction = True
instrument.close_port_after_each_call = True
instrument.debug = True

print("=== ETILENO RELAY 4 ON ===")

# Relay 4 = coil address 3
instrument.write_bit(3, 1, functioncode=5)

print("ETILENO ON enviado OK")

estado = instrument.read_bit(3, functioncode=1)
print(f"Estado leído Relay 4 = {estado}")