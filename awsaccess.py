from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import os
import threading

import util
import Temp
import shared


# =========================================================
# VARIABLES
# =========================================================

mensaje_lock = threading.Lock()
mensaje_recibido = None


# =========================================================
# CALLBACK CONEXIÓN
# =========================================================

def on_connect(
    client,
    userdata,
    flags,
    rc
):

    if rc == 0:

        util.logging.info(
            "Conexión exitosa con AWS IoT."
        )

    else:

        util.logging.error(
            "Conexión fallida con AWS IoT. "
            f"Código de error: {rc}"
        )


# =========================================================
# CALLBACK DESCONEXIÓN
# =========================================================

def on_disconnect(
    client,
    userdata,
    rc
):

    if rc != 0:

        util.logging.error(
            "Desconexión inesperada de AWS IoT. "
            f"Código de error: {rc}"
        )

    else:

        util.logging.info(
            "Desconexión exitosa de AWS IoT."
        )


# =========================================================
# RECEPCIÓN MQTT
# =========================================================

def on_message(
    client,
    userdata,
    message
):

    payload = (
        message
        .payload
        .decode("utf-8")
    )

    util.logging.info(
        "[MQTT RX] "
        f"Tópico={message.topic} | "
        f"payload={payload}"
    )

    try:

        recibir_mensaje(
            payload
        )

    except Exception as e:

        util.logging.error(
            "[MQTT RX] "
            "Error procesando mensaje: "
            f"{type(e).__name__}: {e}"
        )


def recibir_mensaje(
    payload
):

    with shared.mensaje_lock:

        shared.mensaje_recibido = (
            payload
        )

    util.logging.info(
        "[MQTT RX] "
        "Mensaje recibido y almacenado."
    )


# =========================================================
# CONEXIÓN AWS IOT
# =========================================================

def connect_to_aws_iot(
    client_id,
    endpoint,
    root_ca,
    private_key,
    certificate,
    port=8883
):

    try:

        mqtt_client = (
            AWSIoTMQTTClient(
                client_id
            )
        )


        mqtt_client.configureEndpoint(
            endpoint,
            port
        )


        mqtt_client.configureCredentials(
            root_ca,
            private_key,
            certificate
        )


        # -------------------------------------------------
        # RECONEXIÓN
        # -------------------------------------------------

        mqtt_client.configureAutoReconnectBackoffTime(
            1,
            32,
            20
        )


        # La cola duradera será manejada por SQLite.
        #
        # La cola interna del SDK puede seguir existiendo
        # durante una conexión, pero no es nuestra
        # persistencia principal.

        mqtt_client.configureOfflinePublishQueueing(0)


        mqtt_client.configureDrainingFrequency(2)


        mqtt_client.configureConnectDisconnectTimeout(30)


        mqtt_client.configureMQTTOperationTimeout(5)


        mqtt_client.onConnect = (on_connect)


        # -------------------------------------------------
        # CONECTAR
        # -------------------------------------------------

        mqtt_client.connect()


        util.logging.info(
            "[AWS] "
            "Conexión exitosa con AWS IoT | "
            f"client_id={client_id}"
        )


        return mqtt_client


    except Exception as e:

        util.logging.error(
            "[AWS] "
            "Error conectando con AWS IoT: "
            f"{type(e).__name__}: {e}"
        )


        return None


# =========================================================
# CONEXIÓN USANDO .ENV
# =========================================================

def connect_to_mqtt():

    try:

        return connect_to_aws_iot(

            os.getenv(
                "CLIENT_ID"
            ),

            os.getenv(
                "ENDPOINT"
            ),

            os.getenv(
                "ROOT_CA"
            ),

            os.getenv(
                "PRIVATE_KEY"
            ),

            os.getenv(
                "CERTIFICATE"
            ),

            int(
                os.getenv(
                    "PORT",
                    "8883"
                )
            )
        )

    except Exception as e:

        util.logging.error(
            "[AWS] "
            "Error creando cliente MQTT: "
            f"{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# PUBLICACIÓN MQTT
# =========================================================

def publish_to_topic(
    mqtt_client,
    topic,
    message,
    qos=1
):
    """
    Publica un mensaje MQTT.

    Devuelve:
        True  -> publish() terminó sin excepción.
        False -> no se pudo publicar.

    IMPORTANTE:
    Esta función NO administra ninguna cola.
    La persistencia se manejará en SQLite.
    """

    if mqtt_client is None:

        util.logging.warning(
            "[AWS] "
            "Cliente MQTT no disponible."
        )

        return False


    if not topic:

        util.logging.error(
            "[AWS] "
            "TOPIC no configurado."
        )

        return False


    try:

        resultado = mqtt_client.publish(
            topic,
            message,
            qos
        )


        util.logging.info(
            "[AWS] "
            "Mensaje MQTT publicado | "
            f"qos={qos}"
        )


        # Algunas versiones del SDK pueden devolver
        # True/False y otras simplemente completar
        # publish() sin excepción.
        #
        # False explícito se considera fallo.

        if resultado is False:

            util.logging.error(
                "[AWS] "
                "publish() devolvió False."
            )

            return False


        return True


    except Exception as e:

        util.logging.error(
            "[AWS] "
            "Error publicando mensaje: "
            f"{type(e).__name__}: {e}"
        )


        return False


# =========================================================
# PUBLICACIÓN DE MEDICIONES
# =========================================================

def publish_mediciones(
    mqtt_client,
    mediciones
):
    """
    Publica una medición y devuelve True/False.

    Esta función NO agrega mensajes a una cola.
    """

    hilo_medidor = None

    try:

        hilo_medidor = threading.Thread(
            target=Temp.parpadear_led_500ms
        )

        hilo_medidor.start()


        ok = publish_to_topic(
            mqtt_client=mqtt_client,
            topic=os.getenv(
                "TOPIC"
            ),
            message=mediciones,
            qos=1
        )


        return ok


    except Exception as e:

        util.logging.error(
            "[AWS] "
            "Error publicando medición: "
            f"{type(e).__name__}: {e}"
        )


        return False


    finally:

        if hilo_medidor is not None:

            try:

                hilo_medidor.join(
                    timeout=2
                )

            except Exception:

                pass


# =========================================================
# DESCONEXIÓN
# =========================================================

def disconnect_from_aws_iot(
    mqtt_client
):

    if mqtt_client is None:

        return False


    try:

        mqtt_client.disconnect()


        util.logging.info(
            "[AWS] "
            "Cliente MQTT desconectado."
        )


        return True


    except Exception as e:

        util.logging.error(
            "[AWS] "
            "Error desconectando MQTT: "
            f"{type(e).__name__}: {e}"
        )


        return False


# =========================================================
# RECEPCIÓN DE MENSAJES
# =========================================================

def iniciar_recepcion_mensajes():

    try:

        client_id = (
            os.getenv(
                "CLIENT_ID"
            )
            + "_RX"
        )


        endpoint = os.getenv(
            "ENDPOINT"
        )


        root_ca = os.getenv(
            "ROOT_CA"
        )


        private_key = os.getenv(
            "PRIVATE_KEY"
        )


        certificate = os.getenv(
            "CERTIFICATE"
        )


        topic = os.getenv(
            "TUTOPIC"
        )


        mqtt_client = (
            AWSIoTMQTTClient(
                client_id
            )
        )


        mqtt_client.configureEndpoint(
            endpoint,
            8883
        )


        mqtt_client.configureCredentials(
            root_ca,
            private_key,
            certificate
        )


        mqtt_client.configureOfflinePublishQueueing(
            -1
        )


        mqtt_client.configureDrainingFrequency(
            2
        )


        mqtt_client.configureConnectDisconnectTimeout(
            10
        )


        mqtt_client.configureMQTTOperationTimeout(
            5
        )


        mqtt_client.connect()


        util.logging.info(
            "[MQTT RX] "
            "Conectado y escuchando "
            "en segundo plano."
        )


        mqtt_client.subscribe(
            topic,
            1,
            on_message
        )


        return mqtt_client


    except Exception as e:

        util.logging.error(
            "[MQTT RX] "
            "Error al conectar o suscribirse: "
            f"{type(e).__name__}: {e}"
        )


        return None