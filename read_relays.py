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

print("Leyendo 8 coils...")

estados = inst.read_bits(
    registeraddress=0,
    number_of_bits=8,
    functioncode=1
)

print("Estados:", estados)