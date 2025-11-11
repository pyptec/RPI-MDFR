# datos_iniciales.py
import json
import util
import Temp
import awsaccess
import fileventqueue
import eventHandler

def ejecutar_datos_iniciales(obtener_datos_medidores_y_sensor):
    """
    Tarea de arranque del sistema:
    - Conexión a AWS IoT
    - Lectura inicial de sensores Modbus
    - Publicación de datos o almacenamiento local si falla
    - Verificación de temperatura y watchdog
    """

    try:
        # === Conexión AWS (identificación de dispositivo) ===
        conneced_aws = json.dumps(eventHandler.pyp_Conect())

        # === Medición inicial de sensores ===
        datos = obtener_datos_medidores_y_sensor()

        # === Iniciar watchdog ===
        Temp.iniciar_wdt()

        # === Verificar conexión a Internet ===
        if util.ensure_internet_failover():
            mqtt_client = awsaccess.connect_to_mqtt()
            if mqtt_client:
                util.logging.info("[INICIO] Conectado a AWS IoT. Publicando datos iniciales...")

                awsaccess.publish_mediciones(mqtt_client, conneced_aws)
                awsaccess.publish_mediciones(mqtt_client, datos['sensor_CT01CO2'])
                awsaccess.publish_mediciones(mqtt_client, datos['sensor_THT03R'])

                awsaccess.disconnect_from_aws_iot(mqtt_client)
                util.logging.info("[INICIO] Publicación inicial completada.")
            else:
                util.logging.error("[INICIO] No hay conexión MQTT. Guardando eventos localmente.")
                fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
                fileventqueue.agregar_evento(datos['sensor_THT03R'])
                fileventqueue.agregar_evento(conneced_aws)
        else:
            util.logging.error("[INICIO] Sin conexión a Internet. Guardando eventos localmente.")
            fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
            fileventqueue.agregar_evento(datos['sensor_THT03R'])
            fileventqueue.agregar_evento(conneced_aws)

        # === Verificar temperatura del CPU ===
        Temp.check_temp()

    except Exception as e:
        util.logging.error(f"[INICIO] Error general en ejecutar_datos_iniciales(): {type(e).__name__}: {e}")
