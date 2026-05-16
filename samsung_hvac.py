#!/usr/bin/env python3
import os
import time
import serial
import minimalmodbus
import util
from dotenv import load_dotenv

load_dotenv("/home/pi/.scr/.scr/RPI-MDFR/.env")


def _cfg():
    return util.cargar_configuracion(
        os.getenv("CFG_SAMSUNG"),
        os.getenv("CFG_SAMSUNG_SECTION")
    )


def _inst(cfg):
    port = cfg.get("port", "/dev/ttyUSB0")
    slave = int(cfg.get("slave_id", 1))

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = int(cfg.get("baudrate", 9600))
    ser.bytesize = int(cfg.get("bytesize", 8))
    ser.stopbits = int(cfg.get("stopbits", 1))
    ser.timeout = float(cfg.get("timeout", 1))
    ser.write_timeout = 2.0
    ser.inter_byte_timeout = 0.2
    ser.parity = serial.PARITY_EVEN

    ser.xonxoff = False
    ser.rtscts = False
    ser.dsrdtr = False

    # Evita BrokenPipeError por DTR/RTS en algunos USB-RS485
    ser.dtr = False
    ser.rts = False

    ser.open()

    inst = minimalmodbus.Instrument(port, slave)
    inst.serial = ser

    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = False

    return inst

def activar_debug_tx_rx(inst):
    original_write = inst.serial.write
    original_read = inst.serial.read

    def write_debug(data):
        print("TX:", data.hex(" ").upper())
        return original_write(data)

    def read_debug(size=1):
        data = original_read(size)
        if data:
            print("RX:", data.hex(" ").upper())
        else:
            print("RX: TIMEOUT / SIN RESPUESTA")
        return data

    inst.serial.write = write_debug
    inst.serial.read = read_debug


def read_status():
    cfg = _cfg()
    inst = _inst(cfg)

    print("\n=== TEST SAMSUNG HVAC ===")
    print(f"Puerto    : {cfg.get('port', '/dev/ttyUSB0')}")
    print(f"Slave ID  : {cfg.get('slave_id', 1)}")
    print(f"Baudrate  : {cfg.get('baudrate', 9600)}")
    print(f"Bytesize  : {cfg.get('bytesize', 8)}")
    print(f"Parity    : {cfg.get('parity', 'E')}")
    print(f"Stopbits  : {cfg.get('stopbits', 1)}")
    print(f"Timeout   : {cfg.get('timeout', 1)}")
    print("\nLeyendo Communication Status register 0...\n")

    activar_debug_tx_rx(inst)

    try:
        status = inst.read_register(
            0,
            0,
            functioncode=3,
            signed=False
        )

        print(f"\nCommunication Status = {status}")

        if status == 7:
            print("HVAC READY")
        elif status == 0:
            print("HVAC NOT READY")
        else:
            print("HVAC estado intermedio")

        return status

    except Exception as e:
        print(f"\nERROR leyendo status: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    read_status()