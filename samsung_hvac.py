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
    inst.serial.bytesize = 8
    inst.serial.stopbits = 1
    inst.serial.timeout = float(cfg.get("timeout", 1))
    inst.serial.inter_byte_timeout = 0.2

    inst.serial.parity = serial.PARITY_EVEN

    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = False

    return inst


def read_status():
    try:
        cfg = _cfg()
        inst = _inst(cfg)

        print("\n=== TEST SAMSUNG HVAC ===")
        print("TX esperado: 01 03 00 00 00 01 84 0A")

        status = inst.read_register(
            0,
            0,
            functioncode=3,
            signed=False
        )

        if status == 0:
            print("RX esperado: 01 03 02 00 00 B8 44")
        elif status == 7:
            print("RX esperado: 01 03 02 00 07 F9 86")

        print(f"Communication Status = {status}")

        if status == 7:
            print("HVAC READY")
        elif status == 0:
            print("HVAC NOT READY")
        else:
            print("HVAC estado intermedio")

        return status

    except Exception as e:
        util.logging.error(
            f"[SAMSUNG_HVAC] Error leyendo status: {type(e).__name__}: {e}"
        )
        return None


if __name__ == "__main__":
    read_status()