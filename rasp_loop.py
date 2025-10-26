# rasp_loop.py
import json
import util
import Temp
import awsaccess
import fileventqueue

def ejecutar_raspberry(tempRaspberry, TIMERCHEQUEOTEMPERATURA, contador_envio):
    """
    Lógica de chequeo del sistema (payload de estado, WDT, envío cada 3 ciclos).
    Devuelve: (tempRaspberry, contador_envio)
    """
    try:
        if tempRaspberry == 0:
            tempRaspberry = TIMERCHEQUEOTEMPERATURA

            # Estado del sistema
            json_estado = util.payload_estado_sistema_y_medidor()
            Sistema = json.dumps(json_estado)

            # Watchdog
            Temp.iniciar_wdt()

            # Envío cada 3 ciclos
            contador_envio += 1
            util.logging.info(f"[RASPBERRY] contador_envio={contador_envio}")

            if contador_envio >= 3:
                contador_envio = 0
                if util.check_internet_connection():
                    mqtt_client = awsaccess.connect_to_mqtt()
                    if mqtt_client:
                        awsaccess.publish_mediciones(mqtt_client, Sistema)
                        awsaccess.disconnect_from_aws_iot(mqtt_client)
                        util.logging.info("[RASPBERRY] Publicación a AWS exitosa.")
                    else:
                        util.logging.warning("[RASPBERRY] No se pudo conectar a AWS IoT Core.")
                else:
                    util.logging.warning("[RASPBERRY] Sin conexión. Evento guardado localmente.")
                    fileventqueue.agregar_evento(Sistema)

        return tempRaspberry, contador_envio

    except Exception as e:
        util.logging.error(f"[RASPBERRY] Error general en ejecutar_raspberry(): {e}")
        return tempRaspberry, contador_envio
