import time
import minimalmodbus
import serial

PORT = "/dev/ttyS0"
SLAVE = 2

inst = minimalmodbus.Instrument(PORT, SLAVE)
inst.serial.baudrate = 9600
inst.serial.bytesize = 8
inst.serial.parity = serial.PARITY_NONE
inst.serial.stopbits = 1
inst.serial.timeout = 1
inst.serial.inter_byte_timeout = 0.2
inst.mode = minimalmodbus.MODE_RTU
inst.clear_buffers_before_each_transaction = True
inst.close_port_after_each_call = True
inst.debug = True

print("=== PRUEBA FC05 coil 0 ON ===")
try:
    inst.write_bit(0, 1, functioncode=5)
    print("FC05 ON enviado OK")
except Exception as e:
    print(f"FC05 ON falló: {type(e).__name__}: {e}")

time.sleep(2)

print("=== PRUEBA FC05 coil 0 OFF ===")
try:
    inst.write_bit(0, 0, functioncode=5)
    print("FC05 OFF enviado OK")
except Exception as e:
    print(f"FC05 OFF falló: {type(e).__name__}: {e}")

time.sleep(2)

print("=== PRUEBA FC15 coils [1,0,0,0,0,0,0,0] ===")
try:
    inst.write_bits(0, [1,0,0,0,0,0,0,0])
    print("FC15 ON enviado OK")
except Exception as e:
    print(f"FC15 ON falló: {type(e).__name__}: {e}")

time.sleep(2)

print("=== PRUEBA FC15 coils [0,0,0,0,0,0,0,0] ===")
try:
    inst.write_bits(0, [0,0,0,0,0,0,0,0])
    print("FC15 OFF enviado OK")
except Exception as e:
    print(f"FC15 OFF falló: {type(e).__name__}: {e}")