#!/usr/bin/env python3
import os
import time
import serial
import minimalmodbus
import util
from dotenv import load_dotenv

load_dotenv("/home/pi/.scr/.scr/RPI-MDFR/.env")

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

    # DEBUG REAL MODBUS
    inst.debug = bool(cfg.get("debug", False))

    return inst


def read_status():
    """
    Communication status:
    7 = Ready
    0 = Not Ready
    """

    try:
        cfg = _cfg()

        # fuerza debug para ver TX/RX
        cfg["debug"] = True

        inst = _inst(cfg)

        print("\n=== DEBUG SAMSUNG HVAC ===\n")

        status = inst.read_register(
            0,
            0,
            functioncode=3,
            signed=False
        )

        util.logging.info(
            f"[SAMSUNG_HVAC] Communication status={status}"
        )

        print(f"\nCommunication Status = {status}\n")

        if status == 7:
            print("HVAC READY")

        elif status == 0:
            print("HVAC NOT READY")

        else:
            print("HVAC estado intermedio")

        return status

    except BrokenPipeError:

        util.logging.error(
            "[SAMSUNG_HVAC] BrokenPipeError en debug minimalmodbus."
        )

        return None

    except Exception as e:

        util.logging.error(
            f"[SAMSUNG_HVAC] Error leyendo status: "
            f"{type(e).__name__}: {e}"
        )

        return None


if __name__ == "__main__":

    print("\n=== TEST SAMSUNG HVAC ===\n")

    read_status()