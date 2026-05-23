import os
import time
import json
import util
import samsung_hvac


_last_hvac_change = 0


def cargar_control_hvac():
    cfg_raw = util.cargar_configuracion(
        os.getenv("CFG_SAMSUNG"),
        os.getenv("CFG_SAMSUNG_SECTION")
    )

    return cfg_raw.get("control", {})


def control_temperatura_banano(payload_tht03r):
    global _last_hvac_change

    try:
        control = cargar_control_hvac()

        if not bool(control.get("enabled", False)):
            util.logging.info("[HVAC_CTRL] Control HVAC deshabilitado por YAML")
            return

        evt = json.loads(payload_tht03r) if isinstance(payload_tht03r, str) else payload_tht03r

        temp_tht = None

        if isinstance(evt, dict):
            d = evt.get("d", [])
            if d and isinstance(d[0], dict):
                v = d[0].get("v", [])
                if len(v) > 0 and v[0] not in [None, "None", ""]:
                    temp_tht = float(v[0])

        if temp_tht is None:
            util.logging.warning("[HVAC_CTRL] Sin temperatura THT03R válida")
            return

        temp_low = float(control.get("temp_low", 19.5))
        temp_high = float(control.get("temp_high", 20.5))

        sp_min = float(control.get("setpoint_min", 16.0))
        sp_max = float(control.get("setpoint_max", 26.0))
        sp_step = float(control.get("setpoint_step", 0.1))

        mode = int(control.get("mode", 1))
        fan = int(control.get("fan_speed", 1))

        min_interval = int(os.getenv("HVAC_MIN_CHANGE_INTERVAL_S", 300))

        ahora = time.time()

        if (ahora - _last_hvac_change) < min_interval:
            util.logging.info(
                f"[HVAC_CTRL] Esperando intervalo mínimo. "
                f"THT03R={temp_tht:.1f} °C"
            )
            return

        status = samsung_hvac.read_status()

        if status != 7:
            util.logging.warning(
                f"[HVAC_CTRL] HVAC no READY. Status={status}"
            )
            return

        current_sp = samsung_hvac.read_setpoint()

        if current_sp is None:
            util.logging.warning("[HVAC_CTRL] No se pudo leer setpoint HVAC")
            return

        nuevo_sp = current_sp
        motivo = "SIN_CAMBIO"

        if temp_tht >= temp_high:
            nuevo_sp = max(sp_min, current_sp - sp_step)
            motivo = "TEMP_ALTA"

        elif temp_tht <= temp_low:
            nuevo_sp = min(sp_max, current_sp + sp_step)
            motivo = "TEMP_BAJA"

        else:
            util.logging.info(
                f"[HVAC_CTRL] TEMP OK | THT03R={temp_tht:.1f} °C | "
                f"SP={current_sp:.1f} °C"
            )
            return

        samsung_hvac.set_mode(mode)
        time.sleep(0.5)

        samsung_hvac.set_fan(fan)
        time.sleep(0.5)

        samsung_hvac.turn_on()
        time.sleep(0.5)

        ok = samsung_hvac.set_temperature(nuevo_sp)

        if ok:
            _last_hvac_change = ahora

            util.logging.info(
                f"[HVAC_CTRL] {motivo} | "
                f"THT03R={temp_tht:.1f} °C | "
                f"SP anterior={current_sp:.1f} °C | "
                f"SP nuevo={nuevo_sp:.1f} °C | "
                f"Modo={mode} | Fan={fan}"
            )

    except Exception as e:
        util.logging.error(f"[HVAC_CTRL] Error controlando HVAC: {type(e).__name__}: {e}")