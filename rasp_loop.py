# rasp_loop.py
import json
import os
import util
import Temp
from webapp.services import db_service

def ejecutar_raspberry(tempRaspberry, TIMERCHEQUEOTEMPERATURA, contador_envio):
    """
    Lógica de chequeo del sistema (payload de estado, WDT, envío cada 3 ciclos).
    Devuelve: (tempRaspberry, contador_envio)
    """
    try:
        if tempRaspberry == 0:
            tempRaspberry = TIMERCHEQUEOTEMPERATURA
            
            # =================================================
            # Estado del sistema
            # =================================================
            json_estado = util.payload_estado_sistema_y_medidor()
            Sistema = json.dumps(json_estado)

            # =================================================
            # Watchdog
            # =================================================
            
            Temp.iniciar_wdt()

            # =================================================
            # ENCOLAR CADA 10 CICLOS
            # =================================================
       
            contador_envio += 1
            util.logging.info(f"[RASPBERRY] contador_envio={contador_envio}")

            if contador_envio >= 10:

                contador_envio = 0

                try:

                    topic = os.getenv("TOPIC")

                    if not topic:
                        raise RuntimeError(
                            "TOPIC no configurado en .env"
                        )

                    queue_id = db_service.aws_queue_agregar(
                        topic=topic,
                        payload=Sistema
                    )

                    util.logging.info(
                        "[RASPBERRY][AWS_QUEUE] "
                        f"Estado del sistema encolado | "
                        f"id={queue_id}"
                    )

                except Exception as e:

                    util.logging.error(
                        "[RASPBERRY][AWS_QUEUE] "
                        f"Error encolando estado: "
                        f"{type(e).__name__}: {e}"
                    )

        return tempRaspberry, contador_envio

    except Exception as e:
        util.logging.error(f"[RASPBERRY] Error general en ejecutar_raspberry(): {e}")
        return tempRaspberry, contador_envio
