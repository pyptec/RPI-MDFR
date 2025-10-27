import json
import util
import Temp
import modbusdevices



def ejecutar_mdfr(tempMdfr, TIMER_MDFR, obtener_datos_medidores_y_sensor):
    '''
    Ejecuta lectura CT01CO2 (CO2) y THT03R (Temp/Hum) y controla relés:
      - CO2: etileno/extractor según LOW/HIGH en ct01co2.yml
      - Humedad: humidificador según hu_ppm_low / hu_ppm_high en tht03r.yml
      - Temperatura: extractor según temp_c_low / temp_c_high en tht03r.yml (si existen)
    Devuelve tempMdfr actualizado.
    
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
    '''
  
    '''
    Ejecuta lectura CT01CO2 (CO2) y THT03R (Temp/Hum) y controla relés:
      - CO2: etileno/extractor según LOW/HIGH en ct01co2.yml
      - Humedad: humidificador según hu_ppm_low / hu_ppm_high en tht03r.yml
      - Temperatura: extractor según temp_c_low / temp_c_high en tht03r.yml (si existen)
    Devuelve tempMdfr actualizado.
    '''
    try:
        if tempMdfr == 0:
            tempMdfr = TIMER_MDFR

            # === LECTURA DE SENSORES (los dos a la vez) ===
            datos = obtener_datos_medidores_y_sensor()

            # -------------------------------
            # CONTROL POR CO2 (CT01CO2)
            # -------------------------------
            try:
                cfg_raw = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml', 'ct01co2_sensor')
                if isinstance(cfg_raw, dict) and 'control' in cfg_raw:
                    cfg_ct01 = cfg_raw
                else:
                    cfg_full = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml')
                    cfg_ct01 = cfg_full.get('medidores', {}).get('ct01co2_sensor', {})

                ctl_co2 = cfg_ct01.get('control', {})
                CO2_LOW  = int(ctl_co2.get('co2_ppm_low', 5000))
                CO2_HIGH = int(ctl_co2.get('co2_ppm_high', 9000))

                payload_co2 = datos.get('sensor_CT01CO2')  # str JSON o dict
                evt_co2 = json.loads(payload_co2) if isinstance(payload_co2, str) else payload_co2

                co2_raw = None
                if isinstance(evt_co2, dict):
                    d = evt_co2.get('d', [])
                    if d and isinstance(d[0], dict):
                        v = d[0].get('v', [])
                        if v and isinstance(v, list):
                            co2_raw = v[0]

                if co2_raw in [None, "None", ""]:
                    util.logging.warning("CT01CO2 sin dato válido; se omite control CO2 este ciclo.")
                else:
                    co2_ppm = int(float(co2_raw))
                    util.logging.info(f"[MDFR] CO2={co2_ppm} (LOW={CO2_LOW}, HIGH={CO2_HIGH})")

                    if co2_ppm <= CO2_LOW:
                        util.logging.info("[MDFR] CO2→ GAS ON (etileno), EXTRACTOR OFF")
                        Temp.setgas(True)          # etileno (relay4)
                        Temp.setextractor(False)   # extractor (relay2)
                    elif co2_ppm >= CO2_HIGH:
                        util.logging.info("[MDFR] CO2→ GAS OFF (etileno), EXTRACTOR ON")
                        Temp.setgas(False)
                        Temp.setextractor(True)
                    else:
                        util.logging.info("[MDFR] CO2 en banda (sin cambio)")
            except Exception as e:
                util.logging.error(f"No se pudo procesar CO2 para relés: {e}")

            # -------------------------------
            # CONTROL POR HUMEDAD/TEMPERATURA (THT03R)
            # -------------------------------
            try:
                cfg_raw_t = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml', 'tht03r_sensor')
                if isinstance(cfg_raw_t, dict) and 'control' in cfg_raw_t:
                    cfg_tht = cfg_raw_t
                else:
                    cfg_full_t = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml')
                    cfg_tht = cfg_full_t.get('medidores', {}).get('tht03r_sensor', {})

                ctl_env = cfg_tht.get('control', {})  # aquí esperamos hu_ppm_low, hu_ppm_high, temp_c_low, temp_c_high (opc.)

                # Umbrales HUMEDAD (obligatorios para actuar)
                HU_LOW  = ctl_env.get('hu_ppm_low')   # p.ej. 67
                HU_HIGH = ctl_env.get('hu_ppm_high')  # p.ej. 85

                # Umbrales TEMPERATURA (opcionales)
                TEMP_LOW  = ctl_env.get('temp_c_low')   # opcional
                TEMP_HIGH = ctl_env.get('temp_c_high')  # opcional

                payload_tht = datos.get('sensor_THT03R')  # str JSON o dict
                evt_tht = json.loads(payload_tht) if isinstance(payload_tht, str) else payload_tht

                temp_c = None
                hum    = None
                if isinstance(evt_tht, dict):
                    d = evt_tht.get('d', [])
                    if d and isinstance(d[0], dict):
                        v = d[0].get('v', [])
                        if isinstance(v, list):
                            # Convención: v[0] = Temp(°C), v[1] = Hum(%)
                            if len(v) > 0 and v[0] not in [None, "None", ""]:
                                temp_c = float(v[0])
                            if len(v) > 1 and v[1] not in [None, "None", ""]:
                                hum = float(v[1])

                # --- HUMEDAD: controlar humidificador ---
                if hum is None or HU_LOW is None or HU_HIGH is None:
                    util.logging.warning("[MDFR] Humedad: dato/umbrales faltantes; se omite control de humidificador.")
                else:
                    HU_LOW  = float(HU_LOW)
                    HU_HIGH = float(HU_HIGH)
                    util.logging.info(f"[MDFR] HUM={hum}% (LOW={HU_LOW}, HIGH={HU_HIGH})")

                    if hum <= HU_LOW:
                        util.logging.info("[MDFR] HUM→ HUMIDIFICADOR ON (relay3)")
                        Temp.sethumidificador(True)
                    elif hum >= HU_HIGH:
                        util.logging.info("[MDFR] HUM→ HUMIDIFICADOR OFF (relay3)")
                        Temp.sethumidificador(False)
                    else:
                        util.logging.info("[MDFR] HUM en banda (sin cambio)")

                # --- TEMPERATURA: controlar extractor (opcional) ---
                if TEMP_LOW is None and TEMP_HIGH is None:
                    util.logging.info("[MDFR] TEMP: no hay umbrales definidos; sin acción.")
                else:
                    # si hay al menos uno, actuamos según el que exista
                    tlog = []
                    if TEMP_LOW is not None:  tlog.append(f"LOW={TEMP_LOW}")
                    if TEMP_HIGH is not None: tlog.append(f"HIGH={TEMP_HIGH}")
                    util.logging.info(f"[MDFR] TEMP={temp_c}°C ({', '.join(tlog)})")

                    if temp_c is None:
                        util.logging.warning("[MDFR] TEMP: sin dato; se omite control.")
                    else:
                        # Política: si T >= HIGH -> extractor ON; si T <= LOW -> extractor OFF
                        acted = False
                        if TEMP_HIGH is not None and temp_c >= float(TEMP_HIGH):
                            util.logging.info("[MDFR] TEMP→ EXTRACTOR ON (alta T°)")
                            Temp.setrecircular(True)
                            acted = True
                        if TEMP_LOW is not None and temp_c <= float(TEMP_LOW):
                            util.logging.info("[MDFR] TEMP→ EXTRACTOR OFF (baja T°)")
                            Temp.setrecircular(False) #false
                            acted = True
                        if not acted:
                            util.logging.info("[MDFR] TEMP en banda (sin cambio)")

            except Exception as e:
                util.logging.error(f"No se pudo procesar HUM/TEMP para relés: {e}")

        return tempMdfr

    except Exception as e:
        util.logging.error(f"Error general en ejecutar_mdfr(): {e}")
        return tempMdfr


