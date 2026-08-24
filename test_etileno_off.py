import minimalmodbus
import serial

inst = minimalmodbus.Instrument("/dev/ttyS0", 2)
inst.serial.baudrate = 9600
inst.serial.bytesize = 8
inst.serial.parity = serial.PARITY_NONE
inst.serial.stopbits = 1
inst.serial.timeout = 1
inst.mode = minimalmodbus.MODE_RTU
inst.clear_buffers_before_each_transaction = True
inst.close_port_after_each_call = True
inst.debug = True

print("Relay etileno coil 3 -> OFF")
inst.write_bit(3, 0, functioncode=5)
print("Respuesta OK")