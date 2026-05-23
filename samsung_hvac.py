import os
import util




def payload_hvac_status():

    
    try:

        cfg = util.cargar_configuracion(
            os.getenv("CFG_SAMSUNG"),
            os.getenv("CFG_SAMSUNG_SECTION")
        )

        payload = {
            "d": [{
                "t": util.get__time_utc(),
                "g": cfg.get("id_device", 21),

                "v": [
                    str(read_status()),       # 161
                    str(read_onoff()),        # 162
                    str(read_mode()),         # 163
                    str(read_setpoint()),     # 164
                    str(read_room_temp())     # 165
                ],

                "u": [
                    "161",
                    "162",
                    "163",
                    "164",
                    "165"
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

        util.logging.error(
            f"[HVAC] Error payload_hvac_status: {e}"
        )

        return None
    
# =========================================================
# LECTURAS HVAC
# =========================================================

def read_status():
    try:
        return leer_registro(
            REG_STATUS,
            False,
            1,
            "Communication Status"
        )
    except Exception as e:
        util.logging.error(f"[HVAC] read_status: {e}")
        return None


def read_onoff():
    try:
        return leer_registro(
            REG_ONOFF,
            False,
            1,
            "ON/OFF"
        )
    except Exception as e:
        util.logging.error(f"[HVAC] read_onoff: {e}")
        return None


def read_mode():
    try:
        return leer_registro(
            REG_MODE,
            False,
            1,
            "Mode"
        )
    except Exception as e:
        util.logging.error(f"[HVAC] read_mode: {e}")
        return None


def read_setpoint():
    try:
        return leer_registro(
            REG_SETPOINT,
            False,
            10,
            "Setpoint"
        )
    except Exception as e:
        util.logging.error(f"[HVAC] read_setpoint: {e}")
        return None


def read_room_temp():
    try:
        return leer_registro(
            REG_ROOM_TEMP,
            False,
            10,
            "Room Temp"
        )
    except Exception as e:
        util.logging.error(f"[HVAC] read_room_temp: {e}")
        return None   