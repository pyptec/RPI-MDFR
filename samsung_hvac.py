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

    inst = minimalmodbus.Instrument(port, slave)

    inst.serial.baudrate = int(cfg.get("baudrate", 9600))
    inst.serial.bytesize = int(cfg.get("bytesize", 8))
    inst.serial.stopbits = int(cfg.get("stopbits", 1))
    inst.serial.timeout = float(cfg.get("timeout", 1))
    inst.serial.inter_byte_timeout = 0.2

    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD
    }

    inst.serial.parity = parity_map.get(
        str(cfg.get("parity", "E")).upper(),
        serial.PARITY_EVEN
    )

    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True

    # NO usar debug interno porque genera BrokenPipeError
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