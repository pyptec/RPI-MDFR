from dotenv import load_dotenv
from mdfr_loop import ejecutar_mdfr
from rasp_loop import ejecutar_raspberry
from datos_iniciales import ejecutar_datos_iniciales
from webapp.services import db_service

import os
import time
import json
import util
import struct
import awsaccess
import Temp

import threading
import eventHandler
import shared
import subprocess
import modbusdevices
import random
import samsung_hvac
# import tunel_watcher

# Dispatcher simple
DISPATCH = {
    "raspberry": ejecutar_raspberry,  # espera: (tempRaspberry, TIMERCHEQUEOTEMPERATURA, contador_envio)
    "mdfr": ejecutar_mdfr,            # espera: (tempMdfr, TIMER_MDFR, obtener_datos_medidores_y_sensor)
}

# Ruta al archivo .env
load_dotenv(dotenv_path="/home/pi/.scr/.scr/RPI-MDFR/.env")

# Leer variables como enteros
TIMERCHEQUEOTEMPERATURA = int(os.getenv('TIMERCHEQUEOTEMPERATURA', 60))
TIMERCOLAEVENTOS = int(os.getenv('TIMERCOLAEVENTOS', 60))
TIMERMEDICION = int(os.getenv('TIMERMEDICION', 600))
TIMERPING = int(os.getenv('TIMERPING', 120))
TIMECHECKUSBETHERNET = int(os.getenv('TIMECHECKUSBETHERNET', 600))
TIMECHECK_USB_ETHERNET_TIME = int(os.getenv('TIMECHECK_USB_ETHERNET_TIME', 6))
TIMER_MDFR = int(os.getenv('TIMER_MDFR', 6))

# ------------------- Watcher de failover (ETH→USB) en segundo plano -------------------
def _failover_loop(period=30):
    while True:
        try:
            util.ensure_internet_failover()
        except Exception as e:
            util.logging.exception(f"failover loop error: {e}")
        time.sleep(period)

# Lanza el watcher
threading.Thread(target=_failover_loop, args=(30,), daemon=True).start()
# --------------------------------------------------------------------------------------
#prueba de relay
# --------------------------------------------------------------------------------------
def prueba_relays():
    cfg = Temp._cfg_relays()

    util.logging.info("=== PRUEBA MANUAL DE RELAYS ===")

    relay_names = [
        str(reg['name'])
        for reg in cfg.get('registers', [])
        if int(reg.get('fc_read', 0)) == 1 and int(reg.get('fc_write', 0)) == 5
    ]
    for nombre in relay_names:
        util.logging.info(f"Prueba {nombre} ON")
        modbusdevices.relay_set(cfg, nombre, True)
        time.sleep(3)

        util.logging.info(f"Prueba {nombre} OFF")
        modbusdevices.relay_set(cfg, nombre, False)
        time.sleep(2)

    util.logging.info("=== FIN PRUEBA MANUAL DE RELAYS ===")
# =========================================================
# PROCESAR COLA AWS DESDE SQLITE
# =========================================================

def process_event_queue():
    """
    Procesa la cola persistente AWS almacenada en SQLite.

    Flujo:
        aws_queue PENDING
            -> conexión AWS
            -> publicación MQTT QoS 1
            -> SENT si publish_to_topic() retorna True
            -> permanece PENDING si falla

    La fila NO se elimina de SQLite.
    """

    mqtt_client = None

    try:

        # =====================================================
        # OBTENER EVENTOS PENDIENTES
        # =====================================================

        pendientes = (
            db_service.aws_queue_obtener_pendientes(
                limite=48
            )
        )


        if not pendientes:

            util.logging.info(
                "[AWS_QUEUE] No hay eventos pendientes."
            )

            return


        util.logging.info(
            "[AWS_QUEUE] "
            f"Pendientes encontrados: {len(pendientes)}"
        )


        # =====================================================
        # COMPROBAR INTERNET
        # =====================================================

        if not util.ensure_internet_failover():

            util.logging.warning(
                "[AWS_QUEUE] Sin conexión a Internet."
            )

            return


        # =====================================================
        # CONECTAR AWS
        # =====================================================

        mqtt_client = (awsaccess.connect_to_mqtt() )


        if mqtt_client is None:

            util.logging.warning(
                "[AWS_QUEUE] "
                "No fue posible conectar con AWS IoT."
            )

            return


        # =====================================================
        # PROCESAR FIFO
        # =====================================================

        for evento in pendientes:

            queue_id = evento["id"]

            topic = evento["topic"]

            payload = evento["payload_json"]


            try:

                util.logging.info(
                    "[AWS_QUEUE] "
                    f"Publicando id={queue_id} | "
                    f"topic={topic}"
                )


                # LED de actividad
                hilo_led = threading.Thread(
                    target=Temp.parpadear_led_500ms
                )

                hilo_led.start()


                ok = awsaccess.publish_to_topic(
                    mqtt_client=mqtt_client,
                    topic=topic,
                    message=payload,
                    qos=1
                )


                hilo_led.join()


                # =================================================
                # PUBLICACIÓN CORRECTA
                # =================================================

                if ok:

                    db_service.aws_queue_marcar_enviado(
                        queue_id
                    )


                    util.logging.info(
                        "[AWS_QUEUE] "
                        f"id={queue_id} -> SENT"
                    )


                # =================================================
                # PUBLICACIÓN FALLIDA
                # =================================================

                else:

                    error = (
                        "publish_to_topic devolvio False"
                    )


                    db_service.aws_queue_marcar_error(
                        queue_id,
                        error
                    )


                    util.logging.warning(
                        "[AWS_QUEUE] "
                        f"id={queue_id} -> PENDING | "
                        f"{error}"
                    )


                    # Si falla un mensaje, detener el lote.
                    # Evita intentar decenas de publicaciones
                    # con una conexión posiblemente caída.
                    break


            except Exception as e:

                error = (
                    f"{type(e).__name__}: {e}"
                )


                db_service.aws_queue_marcar_error(
                    queue_id,
                    error
                )


                util.logging.error(
                    "[AWS_QUEUE] "
                    f"id={queue_id} -> PENDING | "
                    f"{error}"
                )


                break


        # =====================================================
        # RESUMEN
        # =====================================================

        pendientes_restantes = (
            db_service.aws_queue_contar_pendientes()
        )


        util.logging.info(
            "[AWS_QUEUE] "
            f"Procesamiento terminado | "
            f"pendientes={pendientes_restantes}"
        )


    except Exception as e:

        util.logging.error(
            "[AWS_QUEUE] "
            "Error general procesando cola: "
            f"{type(e).__name__}: {e}"
        )


    finally:

        if mqtt_client is not None:

            try:

                awsaccess.disconnect_from_aws_iot(
                    mqtt_client
                )

            except Exception as e:

                util.logging.warning(
                    "[AWS_QUEUE] "
                    "Error desconectando MQTT: "
                    f"{type(e).__name__}: {e}"
                )
# =========================================================
# PROCESAMIENTO DE CICLOS CO2 LOW -> HIGH
# =========================================================

def procesar_ciclo_co2_actual(payload_co2):
    """
    Procesa el valor actual de CO2 para detectar ciclos
    LOW -> HIGH durante un proceso de maduración activo.

    La función:
    - NO controla relés.
    - NO modifica el YAML.
    - NO publica a AWS.
    - Solo registra ciclos en SQLite.
    """

    try:

        # -------------------------------------------------
        # PAYLOAD
        # -------------------------------------------------

        if payload_co2 is None:
            return

        if isinstance(payload_co2, str):

            payload = json.loads(payload_co2)

        else:

            payload = payload_co2


        if not isinstance(payload, dict):
            return


        datos = payload.get("d",[])

        if not datos:
            return


        registro = datos[0]

        valores = registro.get("v", [])

        if not valores:
            return


        valor_co2 = valores[0]


        if valor_co2 in [
            None,
            "None",
            ""
        ]:
            return


        valor_co2 = float(
            valor_co2
        )


        # -------------------------------------------------
        # TIMESTAMP ORIGINAL DEL SENSOR
        # -------------------------------------------------

        timestamp_utc = registro.get("t")


        # -------------------------------------------------
        # CONFIGURACIÓN CT01CO2
        # -------------------------------------------------

        config = (util.cargar_configuracion(os.getenv("CFG_CT01CO2"), os.getenv("CFG_CT01CO2_SECTION" )))


        control = config.get("control", {})


        co2_low = float(control.get("co2_ppm_low", 3000 ))


        co2_high = float(control.get("co2_ppm_high", 9000))


        # -------------------------------------------------
        # PROCESAR CICLO
        # -------------------------------------------------

        resultado = (
            db_service.procesar_ciclo_co2(
                valor_co2=valor_co2,
                timestamp_utc=timestamp_utc,
                co2_low=co2_low,
                co2_high=co2_high
            )
        )


        if not resultado:
            return


        evento = resultado.get(
            "evento"
        )


        # -------------------------------------------------
        # LOG SOLO SI HUBO CAMBIO DE ESTADO
        # -------------------------------------------------

        if evento == "CICLO_ABIERTO":

            util.logging.info(
                "[CO2-CICLO] "
                f"Ciclo abierto | "
                f"CO2={valor_co2:.0f} ppm | "
                f"LOW={co2_low:.0f} ppm | "
                f"id={resultado.get('id')}"
            )


        elif evento == "CICLO_CERRADO":

            duracion = float(resultado.get("duracion_segundos", 0 ))

            horas = (duracion / 3600.0)

            util.logging.info(
                "[CO2-CICLO] "
                f"Ciclo cerrado | "
                f"CO2={valor_co2:.0f} ppm | "
                f"HIGH={co2_high:.0f} ppm | "
                f"duracion={horas:.2f} h | "
                f"id={resultado.get('id')}"
            )


    except Exception as e:

        # Esta función jamás debe detener
        # el control de la cámara.

        util.logging.error(
            "[CO2-CICLO] "
            f"Error procesando ciclo: "
            f"{type(e).__name__}: {e}"
        )

#-----------------------------------------------------------------------------------------------------------   
# Rutina de lectura de sensores Modbus RTU y devuelve datos en formato JSON 
#-----------------------------------------------------------------------------------------------------------    
def obtener_datos_medidores_y_sensor(promediar=False):
    """
    Lee los sensores:
    - CT01CO2
    - THT03R
    - PT21A01

    Si alguno no responde:
    - deja valores en None
    - registra error en log

    Devuelve un diccionario donde cada valor es JSON.
    """
    try:
        # === SENSOR 1 — CT01CO2 ===
        try:
            config_CT01CO2  = util.cargar_configuracion(os.getenv("CFG_CT01CO2"), os.getenv("CFG_CT01CO2_SECTION"))
            #config_CT01CO2 = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml','ct01co2_sensor')            
            g_ct01 = config_CT01CO2.get('id_device')
            simular = bool(config_CT01CO2.get('simular', False))
            
            if simular:
                co2_simulado = random.randint(800, 9600)
                util.logging.info(f"[CT01CO2] SIM → CO₂ = {co2_simulado} ppm")
                medicion_CT01CO2 = {
                    "d": [{
                        "t": util.get__time_utc(),
                        "g": g_ct01,
                        "v": [str(co2_simulado)],
                        "u": ["139"]
                    }]
                }
            else:
                medicion_CT01CO2 = modbusdevices.payload_event_modbus(config_CT01CO2)
                if medicion_CT01CO2 is None:
                    util.logging.warning("CT01CO2 sin respuesta.")
                    medicion_CT01CO2 = {
                        "d": [{"t": util.get__time_utc(), "g": g_ct01, "v": [None], "u": [None]}]
                    }
                else:
                    try:
                        valor_co2 = medicion_CT01CO2["d"][0]["v"][0]
                        if valor_co2 not in [None, "None"]:
                            util.logging.info(f"CT01CO2 → {valor_co2} ppm")
                        else:
                            util.logging.warning("CT01CO2 sin valor válido (None)")
                    except Exception:
                        util.logging.warning(f"CT01CO2: payload inesperado (g={g_ct01})")
        except Exception as e:
            util.logging.error(f"Error CT01CO2: {e}")
            medicion_CT01CO2 = {
                "d": [{"t": util.get__time_utc(), "g": g_ct01, "v": [None], "u": [None]}]
            }

        medicionSensorCT01CO2 = json.dumps(medicion_CT01CO2)
        # =========================================================
        # DETECCIÓN CICLO CO2 LOW -> HIGH
        # =========================================================

        #procesar_ciclo_co2_actual(medicionSensorCT01CO2)
        # =========================================================
        # === SENSOR 2 — THT03R ===
        # =========================================================
        try:
            config_THT03R = util.cargar_configuracion(os.getenv("CFG_THT03R"),os.getenv("CFG_THT03R_SECTION"))
            #config_THT03R = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml', 'tht03r_sensor')
            g_tht03r = config_THT03R.get('id_device')
            simular = bool(config_THT03R.get('simular', False))

            if simular:
                
                temp_simulada = round(random.uniform(17.5, 19.5), 1)
                hum_simulada = round(random.uniform(85.0, 95.0), 1)
                regs = config_THT03R.get('registers', [])
                unidades = [str(r.get('unit')) for r in regs]
                
                util.logging.info(f"[THT03R] SIM → Temp={temp_simulada} °C, Hum={hum_simulada} %")
                
                medicion_THT03R = {
                    "d": [{
                        "t": util.get__time_utc(),
                        "g": g_tht03r,
                        "v": [str(temp_simulada), str(hum_simulada)],
                        "u": unidades
                    }]
                }
                
            else:
                if promediar:
                    #medicion_THT03R = modbusdevices.payload_event_modbus(config_THT03R)
                    medicion_THT03R = modbusdevices.payload_event_modbus_promedio(config_THT03R, muestras=10, delay_s=0.2, decimales=1)
                else:
                    #medicion_THT03R = modbusdevices.payload_event_modbus_promedio(config_THT03R, muestras=10, delay_s=0.2, decimales=1)
                    medicion_THT03R = modbusdevices.payload_event_modbus(config_THT03R)
                if medicion_THT03R is None:
                    util.logging.warning("THT03R sin respuesta.")
                    medicion_THT03R = {
                        "d": [{"t": util.get__time_utc(), "g":  g_tht03r, "v": [None, None], "u": [None, None]}]
                    }
                else:
                    valores = medicion_THT03R["d"][0]["v"]
                    temp = valores[0] if len(valores) > 0 else None
                    hum  = valores[1] if len(valores) > 1 else None

                    if temp not in [None, "None"] or hum not in [None, "None"]:
                        util.logging.info(f"THT03R → Temp={temp} °C, Hum={hum} %")
                    else:
                        util.logging.warning("THT03R sin valores válidos (None)")
        except Exception as e:
            util.logging.error(f"Error THT03R: {e}")
            medicion_THT03R = {
                "d": [{"t": util.get__time_utc(), "g":  g_tht03r, "v": [None, None], "u": [None, None]}]
            }

        medicionSensorTHT03R = json.dumps(medicion_THT03R)
     
     
     
        # =========================================================
        # SENSOR 3 — PT21A01
        # =========================================================
        try:

            config_PT21A01 = util.cargar_configuracion(os.getenv("CFG_PT21A01"), os.getenv("CFG_PT21A01_SECTION"))          

            g_pt21 = config_PT21A01.get('id_device')

            simular = bool(config_PT21A01.get('simular', False))

            if simular:

                temp_pulpa = round(random.uniform(16.0, 20.0), 1)
                resistencia = round(random.uniform(100.0, 120.0), 1)

                regs = config_PT21A01.get('registers', [])

                unidades = [
                    str(r.get('unit'))
                    for r in regs
                ]

                util.logging.info(f"[PT21A01] SIM → " f"Temp={temp_pulpa} °C, " f"R={resistencia} Ω")

                medicion_PT21A01 = {
                    "d": [{
                        "t": util.get__time_utc(),
                        "g": g_pt21,
                        "v": [
                            str(temp_pulpa),
                            str(resistencia)
                        ],
                        "u": unidades
                    }]
                }

            else:
                if promediar:
                    #medicion_PT21A01 = (modbusdevices.payload_event_modbus(config_PT21A01))
                    medicion_PT21A01 = modbusdevices.payload_event_modbus_promedio(config_PT21A01, muestras=10, delay_s=0.2, decimales=1)

                else:
                    #medicion_PT21A01 = modbusdevices.payload_event_modbus_promedio(config_PT21A01, muestras=10, delay_s=0.2, decimales=1)
                    medicion_PT21A01 = (modbusdevices.payload_event_modbus(config_PT21A01))
                if medicion_PT21A01 is None:

                    util.logging.warning("PT21A01 sin respuesta.")

                    medicion_PT21A01 = {
                        "d": [{
                            "t": util.get__time_utc(),
                            "g": g_pt21,
                            "v": [None, None],
                            "u": [None, None]
                        }]
                    }

                else:

                    valores = (medicion_PT21A01["d"][0]["v"])

                    temp = (valores[0] if len(valores) > 0 else None)

                    resistencia = (valores[1] if len(valores) > 1 else None)

                    if (temp not in [None, "None"] or resistencia not in [None, "None"]):

                        util.logging.info(f"[PT21A01] → " f"Temp={temp} °C, " f"R={resistencia} Ω" )

                    else:

                        util.logging.warning("PT21A01 sin valores válidos (None)")

        except Exception as e:

            util.logging.error(f"Error PT21A01: {e}")

            medicion_PT21A01 = {
                "d": [{
                    "t": util.get__time_utc(),
                    "g": g_pt21,
                    "v": [None, None],
                    "u": [None, None]
                }]
            }

        medicionSensorPT21A01 = json.dumps(medicion_PT21A01)
        
        # =========================================================
        # === SENSOR 3 — C2H4 / ETILENO ===
        # =========================================================

        try:

            config_C2H4 = util.cargar_configuracion(os.getenv("CFG_C2H4"), os.getenv("CFG_C2H4_SECTION"))

            # config_C2H4 = util.cargar_configuracion(
            #     '/home/pi/.scr/.scr/RPI-MDFR/device/c2h4.yml',
            #     'c2h4_sensor'
            # )

            g_c2h4 = config_C2H4.get('id_device')

            simular = bool(config_C2H4.get('simular', False))

            if simular:

                hum_simulada = round(random.uniform(50.0, 70.0), 1)
                temp_simulada = round(random.uniform(18.0, 22.0), 1)
                c2h4_simulado = round(random.uniform(0.0, 150.0), 1)

                regs = config_C2H4.get('registers', [])
                unidades = [str(r.get('unit')) for r in regs]

                util.logging.info(
                    f"[C2H4] SIM → "
                    f"Hum={hum_simulada} %, "
                    f"Temp={temp_simulada} °C, "
                    f"C2H4={c2h4_simulado} ppm"
                )

                medicion_C2H4 = {
                    "d": [{
                        "t": util.get__time_utc(),
                        "g": g_c2h4,
                        "v": [
                            str(hum_simulada),
                            str(temp_simulada),
                            str(c2h4_simulado)
                        ],
                        "u": unidades
                    }]
                }

            else:

                medicion_C2H4 = modbusdevices.payload_event_c2h4(config_C2H4)

                if medicion_C2H4 is None:

                    util.logging.warning("C2H4 sin respuesta.")

                    medicion_C2H4 = {
                        "d": [{
                            "t": util.get__time_utc(),
                            "g": g_c2h4,
                            "v": [None, None, None],
                            "u": [None, None, None]
                        }]
                    }

                else:

                    valores = medicion_C2H4["d"][0]["v"]

                    hum = valores[0] if len(valores) > 0 else None
                    temp = valores[1] if len(valores) > 1 else None
                    c2h4 = valores[2] if len(valores) > 2 else None

                    if (
                        hum not in [None, "None"]
                        or temp not in [None, "None"]
                        or c2h4 not in [None, "None"]
                    ):

                        util.logging.info(
                            f"C2H4 → "
                            f"Hum={hum} %, "
                            f"Temp={temp} °C, "
                            f"C2H4={c2h4} ppm"
                        )

                    else:

                        util.logging.warning(
                            "C2H4 sin valores válidos (None)"
                        )

        except Exception as e:

            util.logging.error(f"Error C2H4: {e}")

            medicion_C2H4 = {
                "d": [{
                    "t": util.get__time_utc(),
                    "g": g_c2h4,
                    "v": [None, None, None],
                    "u": [None, None, None]
                }]
            }

        medicionSensorC2H4 = json.dumps(medicion_C2H4)
        
                # =========================================================
        # === SENSOR 4 — CWT-TM-2PT / PT1000 CANAL 1 ===
        # =========================================================

        try:

            config_CWT = util.cargar_configuracion(
                os.getenv("CFG_CWT"),
                os.getenv("CFG_CWT_SECTION")
            )

            g_cwt = config_CWT.get('id_device')
            simular = bool(config_CWT.get('simular', False))

            if simular:

                temp_simulada = round(
                    random.uniform(17.5, 22.0),
                    1
                )

                regs = config_CWT.get('registers', [])

                # Solo Unit ID del canal 1
                unidad_ch1 = (
                    str(regs[0].get('unit'))
                    if len(regs) > 0
                    else None
                )

                util.logging.info(
                    f"[CWT-PT1000] SIM → CH1 Temp={temp_simulada} °C"
                )

                medicion_CWT = {
                    "d": [{
                        "t": util.get__time_utc(),
                        "g": g_cwt,
                        "v": [str(temp_simulada)],
                        "u": [unidad_ch1]
                    }]
                }

            else:

                if promediar:

                    medicion_CWT_raw = (
                        modbusdevices.payload_event_modbus_promedio(
                            config_CWT,
                            muestras=10,
                            delay_s=0.2,
                            decimales=1
                        )
                    )

                else:

                    medicion_CWT_raw = (
                        modbusdevices.payload_event_modbus(
                            config_CWT
                        )
                    )

                if medicion_CWT_raw is None:

                    util.logging.warning(
                        "CWT-PT1000 CH1 sin respuesta."
                    )

                    medicion_CWT = {
                        "d": [{
                            "t": util.get__time_utc(),
                            "g": g_cwt,
                            "v": [None],
                            "u": [None]
                        }]
                    }

                else:

                    valores = medicion_CWT_raw["d"][0].get("v", [])
                    unidades = medicion_CWT_raw["d"][0].get("u", [])

                    # =============================================
                    # TOMAR ÚNICAMENTE CANAL 1
                    # =============================================

                    temp_pt1000 = (
                        valores[0]
                        if len(valores) > 0
                        else None
                    )

                    unidad_ch1 = (
                        unidades[0]
                        if len(unidades) > 0
                        else None
                    )

                    # Crear nuevo payload exclusivamente con CH1
                    medicion_CWT = {
                        "d": [{
                            "t": medicion_CWT_raw["d"][0].get(
                                "t",
                                util.get__time_utc()
                            ),
                            "g": g_cwt,
                            "v": [temp_pt1000],
                            "u": [unidad_ch1]
                        }]
                    }

                    if temp_pt1000 not in [None, "None"]:

                        util.logging.info(
                            f"CWT-PT1000 → "
                            f"CH1 Temp={temp_pt1000} °C"
                        )

                    else:

                        util.logging.warning(
                            "CWT-PT1000 CH1 sin valor válido (None)"
                        )

        except Exception as e:

            util.logging.error(
                f"Error CWT-PT1000: {e}"
            )

            medicion_CWT = {
                "d": [{
                    "t": util.get__time_utc(),
                    "g": g_cwt,
                    "v": [None],
                    "u": [None]
                }]
            }

        medicionSensorCWT = json.dumps(medicion_CWT)
        
        # =========================================================
        # RETORNO
        # =========================================================
        

        return {
            'sensor_CT01CO2': medicionSensorCT01CO2,
            'sensor_THT03R':  medicionSensorTHT03R,
            'sensor_PT21A01': medicionSensorPT21A01,
            'sensor_C2H4':    medicionSensorC2H4,
            'sensor_CWT':     medicionSensorCWT
        }

    except Exception as e:
        util.logging.error(f"Error general en obtener_datos_medidores_y_sensor: {e}")
        resultado = {'sensor_CT01CO2': json.dumps(None),'sensor_THT03R':  json.dumps(None),'sensor_PT21A01': json.dumps(None)}

        util.logging.info(f"[SENSORES] Resultado → {resultado}")

        return resultado
        
       

def _dns_guard_loop(period=540):  # 9 minutos = 540 s
    """
    Guardia de DNS:
      1) Garantiza conectividad (ETH→USB) con util.ensure_internet_failover().
      2) Si hay ICMP pero no DNS, repara DNS.
      3) Si DNS OK, intenta drenar la cola de eventos.
    """
    while True:
        try:
            ok = util.ensure_internet_failover()  # reusa tu failover (ETH primero, USB curado)
            if ok:
                if not util.dns_ok():
                    if util.icmp_ok():
                        util.logging.warning("Guardia DNS: ICMP OK pero DNS KO; reparando DNS…")
                        util.repair_dns(prefer_iface="usb0")
                # Si tras reparar hay DNS, drena cola
                if util.dns_ok():
                    try:
                        process_event_queue()
                    except Exception as e:
                        util.logging.error(f"Guardia DNS: error al procesar cola: {e}")
            else:
                util.logging.warning("Guardia DNS: sin conectividad IP por eth0 ni usb0.")
        except Exception as e:
            util.logging.exception(f"Guardia DNS: excepción: {e}")
        time.sleep(period)
# Lanza el guardia DNS cada 9 minutos (daemon)
threading.Thread(target=_dns_guard_loop, args=(540,), daemon=True).start()
def aws_publish_loop():
    util.logging.info(
        f"[AWS_LOOP] Thread iniciado. Primera publicación en {TIMERMEDICION} s"
    )

    while True:
        time.sleep(TIMERMEDICION)

        inicio = time.monotonic()

        publicar_mediciones_aws()

        duracion = round(time.monotonic() - inicio, 2)

        util.logging.info(
            f"[AWS_LOOP] Publicación finalizada en {duracion} s. "
            f"Próxima publicación en {TIMERMEDICION} s"
        )
        
def publicar_mediciones_aws():
    try:
        datos = obtener_datos_medidores_y_sensor(promediar=True)
        # =====================================================
        # GUARDAR HISTÓRICO LOCAL SQLITE
        # =====================================================

        try:

            cantidad = db_service.guardar_sensores(datos)

            util.logging.info(f"[DB] Mediciones guardadas localmente: "f"{cantidad}")          

        except Exception as e:

            # La BD jamás debe detener
            # el control de la cámara.

            util.logging.error(f"[DB] Error guardando mediciones: " f"{type(e).__name__}: {e}" )

        
        snap_puerta = Temp.snapshot_puerta()
        snap_man = Temp.snapshot_hombre_atrapado()

        cfg_rel = util.cargar_configuracion(os.getenv("CFG_RELAY"), os.getenv("CFG_RELAY_SECTION"))

        relay_names = [
            str(reg['name'])
            for reg in cfg_rel.get('registers', [])
            if int(reg.get('fc_read', 0)) == 1 and int(reg.get('fc_write', 0)) == 5
        ]
        p_relays = modbusdevices.payload_relays_many_packed(cfg_rel, relay_names)
        p_hvac = samsung_hvac.payload_hvac_status()
        try:
            regs_by_name = {str(r.get('name')): r for r in cfg_rel.get('registers', [])}

            reg_aire = next(reg for reg in cfg_rel.get('registers', []) if reg.get('type') == 'gpio')
            estado_aire = Temp.getairefresco()

            p_relays["d"][0]["v"].append("1" if estado_aire else "0")
            p_relays["d"][0]["u"].append(str(reg_aire["unit"]))

            util.logging.info(
                f"[RELAYS] {reg_aire['name']} GPIO{reg_aire['gpio']} "
                f"estado={'ON' if estado_aire else 'OFF'}"
            )

        except Exception as e:
            util.logging.error(f"[RELAYS] Error agregando aire_fresco al payload: {e}")

        eventos = [
            datos['sensor_CT01CO2'],
            datos['sensor_THT03R'],
            datos['sensor_PT21A01'],
            datos['sensor_C2H4'],
            datos['sensor_CWT'],
            json.dumps(snap_puerta),
            json.dumps(snap_man),
            json.dumps(p_relays)
        ]
        if p_hvac is not None:
            eventos.append(json.dumps(p_hvac))
        
        # =========================================================
        # COLA PERSISTENTE SQLITE
        # =========================================================
        #
        # Todas las mediciones:
        #
        #   1. se generan
        #   2. se guardan primero en aws_queue
        #   3. luego se intenta drenar la cola
        #
        # Nunca se publica directamente desde aquí.
        # =========================================================

        topic = os.getenv(
            "TOPIC"
        )


        if not topic:

            raise RuntimeError(
                "TOPIC no configurado en .env"
            )


        encolados = 0
        errores_encolado = 0


        for evento in eventos:

            try:

                if evento in [
                    None,
                    "",
                    "None"
                ]:

                    continue


                queue_id = (
                    db_service.aws_queue_agregar(
                        topic=topic,
                        payload=evento
                    )
                )


                if queue_id is not None:

                    encolados += 1

                    util.logging.info(
                        "[AWS_QUEUE] "
                        f"Medición encolada | "
                        f"id={queue_id}"
                    )

                else:

                    errores_encolado += 1

                    util.logging.error(
                        "[AWS_QUEUE] "
                        "No fue posible encolar una medición."
                    )


            except Exception as e:

                errores_encolado += 1

                util.logging.error(
                    "[AWS_QUEUE] "
                    "Error encolando medición: "
                    f"{type(e).__name__}: {e}"
                )


        util.logging.info(
            "[AWS_QUEUE] "
            f"Lote guardado | "
            f"encolados={encolados} | "
            f"errores={errores_encolado}"
        )


        # =========================================================
        # INTENTAR TRANSMITIR
        # =========================================================
        #
        # process_event_queue() comprueba por sí misma:
        #
        # - si existen pendientes
        # - conectividad
        # - conexión MQTT
        # - publicación QoS 1
        # - SENT / PENDING
        #
        # =========================================================

        try:

            process_event_queue()

        except Exception as e:

            # Que AWS falle jamás debe impedir
            # que continúe el control de la cámara.

            util.logging.error(
                "[AWS_QUEUE] "
                "Error intentando drenar cola: "
                f"{type(e).__name__}: {e}"
            )


    except Exception as e:
        util.logging.error(f"[AWS] Error general publicando mediciones: {e}")
#-----------------------------------------------------------------------------------------------------------   
# Lógica principal
def main_loop():
    
    # =====================================================
    # BASE DE DATOS LOCAL
    # =====================================================
    try:
        db_service.init_db()

        util.logging.info("[DB] Base de datos local inicializada.")

    except Exception as e:
        util.logging.error(f"[DB] Error inicializando SQLite: " f"{type(e).__name__}: {e}")
    # =====================================================
    # PROCESO DE MADURACIÓN
    # =====================================================

    try:

        proceso_activo = (
            db_service.obtener_proceso_activo()
        )

        if proceso_activo is None:

            resultado_proceso = (db_service.iniciar_proceso(lote=None, observaciones=("Inicio automático del sistema")))

            if resultado_proceso.get("ok"):

                util.logging.info("[PROCESO] " f"Nuevo proceso automático iniciado | "f"id={resultado_proceso.get('id')} | " f"inicio={resultado_proceso.get('inicio_utc')}")

            else:

                util.logging.warning("[PROCESO] "f"No se pudo iniciar proceso: "f"{resultado_proceso.get('mensaje')}")

        else:

            util.logging.info(
                "[PROCESO] "
                f"Reanudando proceso activo | "
                f"id={proceso_activo.get('id')} | "
                f"inicio={proceso_activo.get('inicio_utc')} | "
                f"lote={proceso_activo.get('lote')}"
            )

    except Exception as e:

        util.logging.error(
            "[PROCESO] "
            f"Error inicializando proceso: "
            f"{type(e).__name__}: {e}"
        )    
        
    # Apagar relays y sirena al iniciar
    Temp.setsirena(False)
    Temp.all_relay()

    # Inicializar temporizadores
    tempRaspberry = TIMERCHEQUEOTEMPERATURA
    tempMedidor   = TIMERMEDICION
    tempQueue     = TIMERCOLAEVENTOS
    tempPing      = TIMERPING
    tempCheckusb  = TIMECHECKUSBETHERNET 
    tempHora      = TIMECHECK_USB_ETHERNET_TIME
    tempMdfr      = TIMER_MDFR

    # Interrupciones
    Temp.setup_door_interrupt()
    Temp.setup_man_button_interrupt()   # GPIO6

    util.logging.info("Sistema encendido.")
    #hilo para publicar mediciones periódicamente a AWS IoT
    threading.Thread(target=aws_publish_loop, daemon=True).start()
    # Gate de puerta
    while True:
        try:
            if not Temp.door_is_open():
                util.logging.info("[START] Puerta CERRADA → arrancando sistema.")
                break
            util.logging.warning("[START] Puerta ABIERTA → modo seguro: relés OFF, sin lecturas.")
            
            Temp.restablecer_sistema_post_puerta()
            
            Temp.iniciar_wdt()
            time.sleep(1.0)
        except Exception as e:
            util.logging.error(f"[START] Error en gate de puerta: {type(e).__name__}: {e}")
            time.sleep(1.0)

    # --- BLOQUE DE ARRANQUE datos_iniciales.py---
    ejecutar_datos_iniciales(obtener_datos_medidores_y_sensor)

    # Bucle principal
    contador_envio = 0
    man_log_activo = False
    door_log_activo = False
    while True:
        # GUARD 0: Hombre atrapado
        if getattr(Temp, "_man_state", {}).get("latched"):

            if not man_log_activo:
                util.logging.warning(
                    "[LOOP] Hombre atrapado ACTIVO → "
                    "sólo sirena/baliza; sin mediciones/control."
                )
                man_log_activo = True

            door_log_activo = False

            Temp.setsirena(True)
            # Temp.setbaliza(True)

            Temp.iniciar_wdt()

            time.sleep(0.2)
            continue

        else:
            man_log_activo = False

        # GUARD 1: Puerta abierta
      
        if Temp.door_is_open():

            if not door_log_activo:
                util.logging.warning(
                    "[LOOP] Puerta ABIERTA → "
                    "sistema bloqueado hasta cierre."
                )
                door_log_activo = True

            Temp.restablecer_sistema_post_puerta()

            Temp.iniciar_wdt()

            time.sleep(0.5)
            continue

        else:
            door_log_activo = False
        #Temp.setbaliza(False)
        Temp.setsirena(False)
        # Actualizar timers
        tempRaspberry, _, tempQueue, tempPing, tempCheckusb, tempMdfr = util.actualizar_temporizadores(
            tempRaspberry, 999999, tempQueue, tempPing, tempCheckusb, tempMdfr
        )

        # Caso “raspberry”
        tempRaspberry, contador_envio = DISPATCH["raspberry"](
            tempRaspberry, TIMERCHEQUEOTEMPERATURA, contador_envio
        )

        # Caso “mdfr”
        tempMdfr = DISPATCH["mdfr"](
            tempMdfr, TIMER_MDFR, obtener_datos_medidores_y_sensor
        )

        

        if tempQueue == 0:
            tempQueue = TIMERCOLAEVENTOS
            process_event_queue()

        if tempPing == 0:
            tempPing = TIMERPING
            ok = util.ensure_internet_failover()
            if ok:
                util.logging.info("Internet OK por al menos una interfaz.")
            else:
                util.logging.warning("Sin Internet por eth0 ni usb0. Intento de recuperación quedará en log.")

       

# Punto de entrada principal
if __name__ == '__main__':
    #prueba_relays()
    
    main_loop()
