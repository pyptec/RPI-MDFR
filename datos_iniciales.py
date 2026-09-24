# datos_iniciales.py
import json
import util
import Temp
import eventHandler
import os
from webapp.services import db_service

def ejecutar_datos_iniciales(obtener_datos_medidores_y_sensor):
    """
    Tarea de arranque del sistema:
    - Conexión a AWS IoT
    - Lectura inicial de sensores Modbus
    - Publicación de datos o almacenamiento local si falla
    - Verificación de temperatura y watchdog
    """

    try:
        # =================================================
        # === Conexión AWS (identificación de dispositivo) ===
        # =================================================
        
        conneced_aws = json.dumps(eventHandler.pyp_Conect())
        
        # =================================================
        # === Medición inicial de sensores ===
        # =================================================
        
        datos = obtener_datos_medidores_y_sensor()
        
        # =================================================
        # === Iniciar watchdog ===
        # =================================================
        
        Temp.iniciar_wdt()
        
        # =================================================
        # === Guardar datos iniciales en cola SQLite ===
        # =================================================

        eventos = [
            conneced_aws,
            datos['sensor_CT01CO2'],
            datos['sensor_THT03R'],
            datos['sensor_PT21A01'],
            datos['sensor_C2H4'],
            datos['sensor_CWT']
        ]

        topic = os.getenv("TOPIC")

        if not topic:
            raise RuntimeError(
                "TOPIC no configurado en .env"
            )

        encolados = 0

        for evento in eventos:

            if evento in [None, "", "None"]:
                continue

            try:

                queue_id = db_service.aws_queue_agregar(
                    topic=topic,
                    payload=evento
                )

                if queue_id is not None:

                    encolados += 1

                    util.logging.info(
                        "[INICIO][AWS_QUEUE] "
                        f"Evento encolado | id={queue_id}"
                    )

            except Exception as e:

                util.logging.error(
                    "[INICIO][AWS_QUEUE] "
                    f"Error encolando evento: "
                    f"{type(e).__name__}: {e}"
                )

        util.logging.info(
            "[INICIO][AWS_QUEUE] "
            f"Datos iniciales guardados | "
            f"total={encolados}"
        )

        # === Verificar temperatura del CPU ===
        Temp.check_temp()

    except Exception as e:
        util.logging.error(f"[INICIO] Error general en ejecutar_datos_iniciales(): {type(e).__name__}: {e}")
