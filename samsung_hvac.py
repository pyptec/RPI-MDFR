import os
import time
import serial
import util


def _cfg():
    return util.cargar_configuracion(os.getenv("CFG_SAMSUNG"), os.getenv("CFG_SAMSUNG_SECTION"))


def _get_var(alias):
    cfg = _cfg()
    for var in cfg.get("variables", []):
        if var.get("alias") == alias:
            return var
    util.logging.error(f"[HVAC] Alias no encontrado en YAML: {alias}")
    return None


def _serial_params():
    cfg = _cfg()
    return {
        "port": cfg.get("port", "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0OI4DA-if00-port0"),
        "slave": int(cfg.get("slave_id", 1)),
        "baudrate": int(cfg.get("baudrate", 9600)),
        "bytesize": int(cfg.get("bytesize", 8)),
        "parity": str(cfg.get("parity", "E")).upper(),
        "stopbits": int(cfg.get("stopbits", 1)),
        "timeout": float(cfg.get("timeout", 2)),
    }


def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, byteorder="little")


def enviar_frame(frame):
    p = _serial_params()

    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
    }

    try:
        with serial.Serial(
            port=p["port"],
            baudrate=p["baudrate"],
            bytesize=p["bytesize"],
            parity=parity_map.get(p["parity"], serial.PARITY_EVEN),
            stopbits=p["stopbits"],
            timeout=p["timeout"],
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            #util.logging.info(f"[HVAC] TX: {frame.hex(' ').upper()}")

            ser.write(frame)
            time.sleep(1)

            rx = ser.read(100)

            #if rx:
                #util.logging.info(f"[HVAC] RX: {rx.hex(' ').upper()}")
            #else:
                #util.logging.warning("[HVAC] RX: TIMEOUT / SIN RESPUESTA")

            return rx

    except Exception as e:
        util.logging.error(f"[HVAC] Error serial: {type(e).__name__}: {e}")
        return None


def _scale_to_divisor(scale):
    if scale is None:
        return 1

    scale = float(scale)

    if scale == 0:
        return 1

    if scale < 1:
        return int(round(1 / scale))

    return scale


def read_variable(alias):
    var = _get_var(alias)

    if not var:
        return None

    p = _serial_params()
    slave = p["slave"]

    reg = int(var.get("address"))
    fc = int(var.get("fc", 3))
    scale = _scale_to_divisor(var.get("scale", 1))
    signed = str(var.get("type", "uint16")).lower() == "int16"

    frame = bytes([
        slave,
        fc,
        (reg >> 8) & 0xFF,
        reg & 0xFF,
        0x00,
        0x01
    ])

    frame += crc16_modbus(frame)

    rx = enviar_frame(frame)

    if not rx:
        return None

    if len(rx) >= 3 and rx[1] & 0x80:
        util.logging.error(
            f"[HVAC] Excepción Modbus leyendo {alias}: código {rx[2]}"
        )
        return None

    if len(rx) < 7:
        util.logging.error(f"[HVAC] Respuesta incompleta leyendo {alias}")
        return None

    raw = int.from_bytes(rx[3:5], byteorder="big", signed=signed)
    value = raw / scale

    util.logging.info(f"[HVAC] {alias} = {value}")

    return value


def write_variable(alias, value):
    var = _get_var(alias)

    if not var:
        return False

    rw = str(var.get("readWrite", "R")).upper()

    if "W" not in rw:
        util.logging.error(f"[HVAC] Variable no escribible: {alias}")
        return False

    p = _serial_params()
    slave = p["slave"]

    reg = int(var.get("address"))
    fc_write = int(var.get("fc_write", 6))
    scale = float(var.get("scale", 1))

    if scale < 1:
        raw_value = int(round(float(value) / scale))
    else:
        raw_value = int(value)

    frame = bytes([
        slave,
        fc_write,
        (reg >> 8) & 0xFF,
        reg & 0xFF,
        (raw_value >> 8) & 0xFF,
        raw_value & 0xFF,
    ])

    frame += crc16_modbus(frame)

    rx = enviar_frame(frame)

    if not rx:
        return False

    if len(rx) >= 3 and rx[1] & 0x80:
        util.logging.error(
            f"[HVAC] Excepción Modbus escribiendo {alias}: código {rx[2]}"
        )
        return False

    util.logging.info(
        f"[HVAC] Escritura OK {alias} valor={value} raw={raw_value}"
    )

    return True


def read_status():
    return read_variable("comm_status")


def read_onoff():
    return read_variable("hvac_onoff")


def read_mode():
    return read_variable("hvac_mode")


def read_fan():
    return read_variable("hvac_fan_speed")


def read_setpoint():
    return read_variable("hvac_setpoint")


def read_room_temp():
    return read_variable("hvac_room_temp")


def read_error():
    return read_variable("hvac_error_code")


def turn_on():
    return write_variable("hvac_onoff", 1)


def turn_off():
    return write_variable("hvac_onoff", 0)


def set_mode(mode):
    return write_variable("hvac_mode", int(mode))


def set_fan(fan):
    return write_variable("hvac_fan_speed", int(fan))


def set_temperature(temp_c):
    return write_variable("hvac_setpoint", float(temp_c))


def payload_hvac_status():
    try:
        cfg = _cfg()

        payload = {
            "d": [{
                "t": util.get__time_utc(),
                "g": cfg.get("id_device", cfg.get("id", 21)),
                "v": [
                    str(read_status()),
                    str(read_onoff()),
                    str(read_mode()),
                    str(read_setpoint()),
                    str(read_room_temp())
                ],
                "u": [
                    str(_get_var("comm_status").get("unit")),
                    str(_get_var("hvac_onoff").get("unit")),
                    str(_get_var("hvac_mode").get("unit")),
                    str(_get_var("hvac_setpoint").get("unit")),
                    str(_get_var("hvac_room_temp").get("unit")),
                ]
            }]
        }

        util.logging.info(
            f"[HVAC] STATUS={payload['d'][0]['v'][0]} | "
            f"ONOFF={payload['d'][0]['v'][1]} | "
            f"MODE={payload['d'][0]['v'][2]} | "
            f"SP={payload['d'][0]['v'][3]} °C | "
            f"ROOM={payload['d'][0]['v'][4]} °C"
        )

        return payload

    except Exception as e:
        util.logging.error(f"[HVAC] Error payload_hvac_status: {e}")
        return None