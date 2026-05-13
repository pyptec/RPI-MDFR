#!/usr/bin/env python3
import os
import time
import serial
import minimalmodbus
import util


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
    inst.debug = bool(cfg.get("debug", False))

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
# SIMULACIÓN
# =========================================================

_SIM = {
    0: 7,      # Communication status
    2: 0,      # OnOff
    3: 1,      # Mode Cool
    4: 0,      # Fan Auto
    8: 200,    # Setpoint 20.0 °C
    9: 195,    # Room temp 19.5 °C
    10: 0      # Error code
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
    """
    Communication status:
    7 = Ready
    """
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
    """
    0=Auto
    1=Cool
    2=Dry
    3=Fan
    4=Heat
    """
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
    """
    0=Auto
    1=Low
    2=Medium
    3=High
    """
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
    """
    Samsung usa décimas:
    20.0 °C -> 200
    """
    try:
        value = int(round(float(temp_c) * 10))
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
    data = {
        "status": read_status(),
        "ready": is_ready(),
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
    """
    RTD 15 °C -> HVAC 16 °C
    RTD 16 °C -> HVAC 17 °C
    RTD 17 °C -> HVAC 18 °C
    RTD 18 °C -> HVAC 19 °C
    RTD >=19 °C -> HVAC 20 °C fijo
    """

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
    """
    Control seguro:
    - valida READY
    - coloca COOL
    - enciende
    - envía setpoint
    """

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
    print(read_all())