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
    inst.debug = bool(cfg.get("debug", False))

    return inst


def read_status():
    try:
        cfg = _cfg()
        cfg["debug"] = True

        inst = _inst(cfg)

        print("\n=== DEBUG SAMSUNG HVAC ===\n")

        status = inst.read_register(
            0,
            0,
            functioncode=3,
            signed=False
        )

        print(f"\nCommunication Status = {status}\n")

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


def is_ready():
    return read_status() == 7


def set_onoff(on=True):
    cfg = _cfg()
    inst = _inst(cfg)
    value = 1 if on else 0
    inst.write_register(2, value, functioncode=6)
    time.sleep(0.2)
    return True


def set_mode_cool():
    cfg = _cfg()
    inst = _inst(cfg)
    inst.write_register(3, 1, functioncode=6)
    time.sleep(0.2)
    return True


def set_temperature(temp_c):
    cfg = _cfg()
    inst = _inst(cfg)
    value = int(round(float(temp_c) * 10))
    inst.write_register(8, value, functioncode=6)
    time.sleep(0.2)
    return True


if __name__ == "__main__":
    print("\n=== TEST SAMSUNG HVAC ===\n")
    read_status()