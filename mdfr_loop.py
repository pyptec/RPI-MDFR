import json
import util
import Temp
import modbusdevices



def ejecutar_mdfr(tempMdfr, TIMER_MDFR, obtener_datos_medidores_y_sensor):
    """
    Ejecuta el bloque de medición CT01CO2 (CO2) y THT03R (Temp/Hum),
    procesando simulación, lectura y control de relés.
    Devuelve el nuevo valor actualizado de tempMdfr.
    """
    try:
        if tempMdfr == 0:
            tempMdfr = TIMER_MDFR

            # === LECTURA DE SENSORES ===
            datos = obtener_datos_medidores_y_sensor()

            # === CONTROL DE RELÉS BASADO EN CO₂ ===
            try:
                # Cargar configuración del CT01CO2 (maneja ambos formatos YAML)
                cfg_raw = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml', 'ct01co2_sensor')
                if isinstance(cfg_raw, dict) and 'control' in cfg_raw:
                    cfg_sensor = cfg_raw
                else:
                    cfg_full = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml')
                    cfg_sensor = cfg_full.get('medidores', {}).get('ct01co2_sensor', {})

                ctl = cfg_sensor.get('control', {})
                CO2_LOW  = int(ctl.get('co2_ppm_low', 5000))
                CO2_HIGH = int(ctl.get('co2_ppm_high', 9000))

                payload = datos.get('sensor_CT01CO2')  # puede ser str JSON o dict
                evt = json.loads(payload) if isinstance(payload, str) else payload

                co2_raw = None
                if isinstance(evt, dict):
                    d = evt.get('d', [])
                    if d and isinstance(d[0], dict):
                        v = d[0].get('v', [])
                        if v and isinstance(v, list):
                            co2_raw = v[0]

                if co2_raw in [None, "None", ""]:
                    util.logging.warning("CT01CO2 sin dato válido; se omite control de relés este ciclo.")
                else:
                    co2_ppm = int(float(co2_raw))
                    
                    util.logging.info(f"CO2 ppm={co2_ppm} (low={CO2_LOW}, high={CO2_HIGH})")

                    if co2_ppm <= CO2_LOW:
                        util.logging.info("[MDFR] Acción → GAS ON (etileno), EXTRACTOR OFF")
                        Temp.setgas(True)
                        Temp.setextractor(False)
                    elif co2_ppm >= CO2_HIGH:
                        util.logging.info("[MDFR] Acción → GAS OFF (etileno), EXTRACTOR ON")
                        Temp.setgas(False)
                        Temp.setextractor(True)
                    else:
                        util.logging.info("[MDFR] En banda (sin cambio de relés)")
                    # Entre LOW y HIGH: mantener estado

            except Exception as e:
                util.logging.error(f"No se pudo procesar CO2 para relés: {e}")

        # Retornar el contador actualizado
        return tempMdfr

    except Exception as e:
        util.logging.error(f"Error general en ejecutar_mdfr(): {e}")
        return tempMdfr


