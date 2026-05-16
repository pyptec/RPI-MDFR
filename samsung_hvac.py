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


def _parity(value):
    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD
    }

    return parity_map.get(
        str(value).upper(),
        serial.PARITY_EVEN
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
    inst.serial.parity = _parity(cfg.get("parity", "E"))

    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True

    # No usar debug de minimalmodbus porque puede producir BrokenPipeError.
    inst.debug = False

    return inst


def _read_register(address, decimals=0, signed=False):
    cfg = _cfg()

    if bool(cfg.get("simular", False)):
        return _sim_read(address)

    inst = _inst(cfg)

    return inst.read_register(
        int(address),
        decimals,
        functioncode=3,
        signed=signed
    )


def _write_register(address, value):
    cfg = _cfg()

    if bool(cfg.get("simular", False)):
        _sim_write(address, value)
        return True

    inst = _inst(cfg)

    inst.write_register(
        int(address),
        int(value),
        functioncode=6
    )

    time.sleep(0.2)

    return True


# =========================================================
# DEBUG RAW MODBUS RTU
# =========================================================

def _crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF

    for b in data:
        crc ^= b

        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    return crc.to_bytes(2, byteorder="little")


def _modbus_read_raw(address, quantity=1):
    cfg = _cfg()

    port = cfg.get("port", "/dev/ttyUSB0")
    slave = int(cfg.get("slave_id", 1))

    pdu = bytes([
        slave,
        0x03,
        (int(address) >> 8) & 0xFF,
        int(address) & 0xFF,
        (int(quantity) >> 8) & 0xFF,
        int(quantity) & 0xFF
    ])

    frame = pdu + _crc16_modbus(pdu)

    print("\n=== DEBUG RAW SAMSUNG HVAC ===")
    print("TX:", frame.hex(" ").upper())

    with serial.Serial(
        port=port,
        baudrate=int(cfg.get("baudrate", 9600)),
        bytesize=int(cfg.get("bytesize", 8)),
        parity=_parity(cfg.get("parity", "E")),
        stopbits=int(cfg.get("stopbits", 1)),
        timeout=float(cfg.get("timeout", 1))
    ) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        ser.write(frame)
        ser.flush()

        expected_len = 5 + (2 * int(quantity))
        rx = ser.read(expected_len)

    print("RX:", rx.hex(" ").upper())

    if len(rx) < 5:
        print("Respuesta incompleta o timeout.")
        return None

    data = rx[:-2]
    crc_rx = rx[-2:]
    crc_calc = _crc16_modbus(data)

    print("CRC recibido :", crc_rx.hex(" ").upper())
    print("CRC calculado:", crc_calc.hex(" ").upper())

    if crc_rx != crc_calc:
        print("CRC inválido.")
        return None

    if rx[1] & 0x80:
        print(f"Respuesta de excepción Modbus. Código: {rx[2]}")
        return None

    value = int.from_bytes(rx[3:5], byteorder="big")

    return value


def read_status_debug_raw():
    value = _modbus_read_raw(0, 1)

    print("\nCommunication Status =", value)

    if value == 7:
        print("HVAC READY")
    elif value == 0:
        print("HVAC NOT READY")
    elif value is None:
        print("Sin respuesta válida")
    else:
        print("HVAC estado intermedio")

    return value


# =========================================================
# SIMULACIÓN
# =========================================================

_SIM = {
    0: 7,
    2: 0,
    3: 1,
    4: 0,
    8: 200,
    9: 195,
    10: 0
}


def _sim_read(address):
    return _SIM.get(int(address), 0)


def _sim_write(address, value):
    _SIM[int(address)] = int(value)
    util.logging.info(
        f"[SAMSUNG_HVAC][SIM] write addr={address} value={value}"
    )


# =========================================================
# FUNCIONES PRINCIPALES
# =========================================================

def read_status():
    try:
        status = _read_register(0)
        util.logging.info(f"[SAMSUNG_HVAC] Communication status={status}")
        return status

    except Exception as e:
        util.logging.error(
            f"[SAMSUNG_HVAC] Error leyendo status: {type(e).__name__}: {e}"
        )
        return None


def is_ready():
    status = read_status()
    return status == 7


def read_onoff():
    try:
        return _read_register(2)
    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error leyendo OnOff: {e}")
        return None


def set_onoff(on=True):
    try:
        value = 1 if on else 0
        _write_register(2, value)
        util.logging.info(f"[SAMSUNG_HVAC] OnOff={'ON' if on else 'OFF'}")
        return True

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error set_onoff: {e}")
        return False


def set_mode(mode=1):
    try:
        _write_register(3, int(mode))
        util.logging.info(f"[SAMSUNG_HVAC] Mode={mode}")
        return True

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error set_mode: {e}")
        return False


def set_mode_cool():
    return set_mode(1)


def set_fan(fan=0):
    try:
        if int(fan) not in [0, 1, 2, 3]:
            util.logging.warning(f"[SAMSUNG_HVAC] Fan inválido: {fan}")
            return False

        _write_register(4, int(fan))
        util.logging.info(f"[SAMSUNG_HVAC] Fan={fan}")
        return True

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error set_fan: {e}")
        return False


def set_temperature(temp_c):
    try:
        temp_c = float(temp_c)
        value = int(round(temp_c * 10))

        _write_register(8, value)

        util.logging.info(
            f"[SAMSUNG_HVAC] Setpoint={temp_c:.1f} °C value={value}"
        )

        return True

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error set_temperature: {e}")
        return False


def read_setpoint():
    try:
        value = _read_register(8)
        return round(value / 10, 1)

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error leyendo setpoint: {e}")
        return None


def read_room_temperature():
    try:
        value = _read_register(9, signed=True)
        return round(value / 10, 1)

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error leyendo room temperature: {e}")
        return None


def read_error_code():
    try:
        return _read_register(10)

    except Exception as e:
        util.logging.error(f"[SAMSUNG_HVAC] Error leyendo error code: {e}")
        return None


def read_all():
    status = read_status()

    data = {
        "status": status,
        "ready": status == 7,
        "onoff": read_onoff(),
        "setpoint": read_setpoint(),
        "room_temperature": read_room_temperature(),
        "error_code": read_error_code()
    }

    util.logging.info(f"[SAMSUNG_HVAC] Estado general: {data}")

    return data


# =========================================================
# CONTROL MDFR
# =========================================================

def calcular_setpoint_por_banano(temp_banano):
    temp_banano = float(temp_banano)

    if temp_banano < 15.5:
        return 16.0
    elif temp_banano < 16.5:
        return 17.0
    elif temp_banano < 17.5:
        return 18.0
    elif temp_banano < 18.5:
        return 19.0
    else:
        return 20.0


def control_por_temperatura_banano(temp_banano):
    setpoint = calcular_setpoint_por_banano(temp_banano)

    if not is_ready():
        util.logging.warning(
            f"[SAMSUNG_HVAC] NOT READY. No se envía setpoint={setpoint}"
        )
        return False, setpoint

    set_mode_cool()
    time.sleep(0.2)

    set_onoff(True)
    time.sleep(0.2)

    ok = set_temperature(setpoint)

    return ok, setpoint


if __name__ == "__main__":
    print("\n=== TEST SAMSUNG HVAC RAW ===")
    read_status_debug_raw()