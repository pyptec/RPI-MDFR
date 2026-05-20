import json
import os
import util
import Temp
import modbusdevices
import time

_aire_fresco_until = 0
_aire_fresco_activo = False


def ejecutar_mdfr(tempMdfr, TIMER_MDFR, obtener_datos_medidores_y_sensor):
    global _aire_fresco_until, _aire_fresco_activo
    try:
        if tempMdfr == 0:
            tempMdfr = TIMER_MDFR

            # === LECTURA DE SENSORES (los dos a la vez) ===
            datos = obtener_datos_medidores_y_sensor()
            # =========================================================
            # RECIRCULACIÓN PERMANENTE DE CÁMARA
            # =========================================================
            #
            # La recirculación mantiene movimiento constante del aire
            # interno de la cámara de maduración para:
            #
            # - homogenizar temperatura,
            # - homogenizar humedad,
            # - distribuir etileno,
            # - evitar estratificación de CO2,
            # - mejorar estabilidad del proceso.
            #
            # Este relay NO depende de temperatura ni CO2.
            # Debe permanecer activo mientras el sistema MDFR
            # esté operando normalmente.
            #
            # Solo debe apagarse en:
            # - emergencia,
            # - hombre atrapado,
            # - puerta abierta,
            # - parada total del sistema.
            #
            try:
                Temp.setrecircular(True)
                util.logging.info("[MDFR] RECIRCULAR ON permanente")
            except Exception as e:
                util.logging.error(
                    f"[MDFR] Error activando recirculación: {e}"
                )

            # -------------------------------
            # CONTROL POR CO2 (CT01CO2)
            # -------------------------------
            try:
                cfg_raw = util.cargar_configuracion(os.getenv("CFG_CT01CO2"), os.getenv("CFG_CT01CO2_SECTION"))
                #cfg_raw = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml', 'ct01co2_sensor')
                if isinstance(cfg_raw, dict) and 'control' in cfg_raw:
                    cfg_ct01 = cfg_raw
                else:
                    cfg_full =util.cargar_configuracion(os.getenv("CFG_CT01CO2"))
                    #cfg_full = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml')
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
                    util.logging.info(f"[CT01CO2] CO2={co2_ppm} ppm | LOW={CO2_LOW} | HIGH={CO2_HIGH}"
)
                    #util.logging.info(f"[MDFR] CO2={co2_ppm} (LOW={CO2_LOW}, HIGH={CO2_HIGH})")

                    
                    minutos_aire = float(ctl_co2.get('aire_fresco_minutos', 2))
                    duracion_s = minutos_aire * 60
                    now = time.monotonic()

                    # =========================================================
                # CONTROL ETILENO / CO2
                # =========================================================
                #
                # Lógica:
                #
                # - Mientras CO2 esté por debajo del HIGH:
                #       ETILENO debe permanecer ON.
                #
                # - Si CO2 supera HIGH:
                #       ETILENO OFF
                #       EXTRACTOR ON
                #       AIRE_FRESCO ON temporizado
                #
                # - Cuando CO2 baja por debajo del LOW:
                #       EXTRACTOR OFF
                #       AIRE_FRESCO OFF
                #
                # Esto evita que el etileno se pierda si el relay
                # se apaga accidentalmente.
                #
                if co2_ppm >= CO2_HIGH:

                    util.logging.warning(f"[CT01CO2] CO2 ALTO={co2_ppm} ppm → " f"ETILENO OFF | EXTRACTOR ON | " f"AIRE_FRESCO ON {minutos_aire} min")

                    Temp.setgas(False)
                    Temp.setextractor(True)

                    if not _aire_fresco_activo:
                        Temp.setairefresco(True)
                        _aire_fresco_activo = True
                        _aire_fresco_until = now + duracion_s

                        util.logging.info("[CT01CO2] AIRE_FRESCO ON")

                else:

                    # =====================================================
                    # REFUERZO ETILENO
                    # =====================================================
                    #
                    # Mientras NO llegue al HIGH,
                    # el gas etileno debe permanecer ON.
                    #
                    Temp.setgas(True)

                    util.logging.info(
                        f"[CT01CO2] CO2={co2_ppm} ppm < HIGH={CO2_HIGH} → " f"ETILENO REFORZADO ON" )

                    if co2_ppm <= CO2_LOW:

                        Temp.setextractor(False)

                        if _aire_fresco_activo:

                            Temp.setairefresco(False)
                            _aire_fresco_activo = False
                            _aire_fresco_until = 0

                            util.logging.info("[CT01CO2] AIRE_FRESCO OFF por CO2 bajo")

                        util.logging.info("[CT01CO2] CO2 BAJO → EXTRACTOR OFF")

                    else:

                        util.logging.info("[CT01CO2] CO2 EN BANDA → ETILENO ON")               
                    
                if _aire_fresco_activo and time.monotonic() >= _aire_fresco_until:
                    Temp.setairefresco(False)
                    _aire_fresco_activo = False
                    _aire_fresco_until = 0
                    util.logging.info("[CT01CO2] ESTADO → AIRE FRESCO OFF por temporizador")
                                       
                  
            except Exception as e:
                util.logging.error(f"No se pudo procesar CO2 para relés: {e}")

            # -------------------------------
            # CONTROL POR HUMEDAD/TEMPERATURA (THT03R)
            # -------------------------------
            try:
                cfg_raw_t = util.cargar_configuracion(os.getenv("CFG_THT03R"), os.getenv("CFG_THT03R_SECTION"))
                #cfg_raw_t = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml', 'tht03r_sensor')
                if isinstance(cfg_raw_t, dict) and 'control' in cfg_raw_t:
                    cfg_tht = cfg_raw_t
                else:
                    cfg_full_t = util.cargar_configuracion(os.getenv("CFG_THT03R"))
                    #cfg_full_t = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml')
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
                            Temp.setrecircular(True) #false
                            acted = True
                        if not acted:
                            util.logging.info("[MDFR] TEMP en banda (sin cambio)")

            except Exception as e:
                util.logging.error(f"No se pudo procesar HUM/TEMP para relés: {e}")

        return tempMdfr

    except Exception as e:
        util.logging.error(f"Error general en ejecutar_mdfr(): {e}")
        return tempMdfr


