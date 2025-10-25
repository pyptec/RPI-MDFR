from dotenv import load_dotenv
import os
import time
import json
import util
import struct
import awsaccess
import Temp
import fileventqueue
import threading
import eventHandler
import shared
import subprocess
import modbusdevices
#import tunel_watcher


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
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def door_interrupt_callback(channel):
    time.sleep(0.05)
    state = Temp.door()
    estado_txt = "Cerrada" if state  == 1 else "Abierta"
    util.logging.warning(f"Puerta Alarma (GPIO6): {estado_txt}")
    estado_sistema = {
                    "t": util.get__time_utc(),
                    "g": 12,
                    "v": [int(state)],
                    "u": [138]  # 1 = °C, 2 = %RAM
                }
    json_estado ={ "d": [estado_sistema] }
    Sistema =json.dumps(json_estado)

    if  util.check_internet_connection():
        mqtt_client = awsaccess.connect_to_mqtt()
        if mqtt_client:
            awsaccess.publish_mediciones(mqtt_client, Sistema)
            awsaccess.disconnect_from_aws_iot(mqtt_client)
    else:
        fileventqueue.agregar_evento(Sistema)

#-----------------------------------------------------------------------------------------------------------    
# Función para procesar eventos en la cola
#-----------------------------------------------------------------------------------------------------------
def process_event_queue():
    if fileventqueue.contar_eventos() != 0:
        if  util.check_internet_connection():
            mqtt_client = awsaccess.connect_to_mqtt()
            if mqtt_client:
                eventos = fileventqueue.procesar_eventos_de_uno_en_uno()
                for evento in eventos:
                    hilo_queue = threading.Thread(target=Temp.parpadear_led_500ms)
                    hilo_queue.start()
                    awsaccess.publish_to_topic(mqtt_client, os.getenv('TOPIC'), evento)
                    time.sleep(0.2)
                    hilo_queue.join()
                awsaccess.disconnect_from_aws_iot(mqtt_client)
                
            else:
                util.logging.info("No se pudo conectar a AWS IoT para procesar la cola de eventos.")
        else:
            util.logging.info("No hay internet para procesar la cola de eventos.")
    else:
        util.logging.info("No hay eventos para procesar.")
        
 #-----------------------------------------------------------------------------------------------------------   
 # Rutina de lectura de sensores Modbus RTU y debuelve datos en formato JSON 
 #-----------------------------------------------------------------------------------------------------------    

def obtener_datos_medidores_y_sensor():
    """
    Lee los sensores CT01CO2 y THT03R.
    Si alguno no responde, deja sus valores en None y lo registra en el log.
    Devuelve un diccionario donde cada valor es una cadena JSON.
    - Devuelve objetos Python con:
        {
          'sensor_CT01CO2': { 'payload': {...}, 'meta': {...} },
          'sensor_THT03R':  { 'payload': {...}, 'meta': {...} }
        }
    """
    try:
        # === SENSOR 1 — CT01CO2 ===
        try:
            config_CT01CO2 = util.cargar_configuracion(
                '/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml',
                'ct01co2_sensor'
            )
            g_ct01 = config_CT01CO2.get('id_device')
            medicion_CT01CO2 = modbusdevices.payload_event_modbus(config_CT01CO2)
            if medicion_CT01CO2 is None:
                util.logging.warning("Sensor CT01CO2 no conectado o sin respuesta.")
                medicion_CT01CO2 = {
                    "d": [{"t": util.get__time_utc(), "g": g_ct01, "v": [None], "u": [None]}]
                }
            else:
                # Extraer valor de CO2 para log
                valor_co2 = medicion_CT01CO2["d"][0]["v"][0]
                if valor_co2 not in [None, "None"]:
                    util.logging.info(f"Lectura CT01CO2 → CO₂ = {valor_co2} ppm")
                else:
                    util.logging.warning("Sensor CT01CO2 sin valor válido (None)")
        except Exception as e:
            util.logging.error(f"Error al leer CT01CO2: {e}")
            medicion_CT01CO2 = {
                "d": [{"t": util.get__time_utc(), "g": g_ct01, "v": [None], "u": [None]}]
            }

        medicionSensorCT01CO2 = json.dumps(medicion_CT01CO2)

        # === SENSOR 2 — THT03R ===
        try:
            config_THT03R = util.cargar_configuracion(
                '/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml',
                'tht03r_sensor'
            )
            g_tht03r = config_THT03R.get('id_device')
            medicion_THT03R = modbusdevices.payload_event_modbus(config_THT03R)
            
            if medicion_THT03R is None:
                util.logging.warning("Sensor THT03R no conectado o sin respuesta.")
                medicion_THT03R = {
                    "d": [{"t": util.get__time_utc(), "g":  g_tht03r, "v": [None, None], "u": [None, None]}]
                }
            else:
                # Extraer valores de temperatura y humedad para log
                valores = medicion_THT03R["d"][0]["v"]
                temp = valores[0] if len(valores) > 0 else None
                hum  = valores[1] if len(valores) > 1 else None

                if temp not in [None, "None"] or hum not in [None, "None"]:
                    util.logging.info(f"Lectura THT03R → Temp = {temp} °C, Hum = {hum} %")
                else:
                    util.logging.warning("Sensor THT03R sin valores válidos (None)")
        except Exception as e:
            util.logging.error(f"Error al leer THT03R: {e}")
            medicion_THT03R = {
                "d": [{"t": util.get__time_utc(), "g":  g_tht03r, "v": [None, None], "u": [None, None]}]
            }

        medicionSensorTHT03R = json.dumps(medicion_THT03R)

        # === Retornar como cadenas JSON ===
        return {
            'sensor_CT01CO2': medicionSensorCT01CO2,
            'sensor_THT03R': medicionSensorTHT03R
        }

    except Exception as e:
        util.logging.error(f"Error general en obtener_datos_medidores_y_sensor: {e}")
        return {
            'sensor_CT01CO2': json.dumps(None),
            'sensor_THT03R': json.dumps(None)
        }

 #-----------------------------------------------------------------------------------------------------------   

# Lógica principal
def main_loop():
    #global ssh_process  
   
    tempRaspberry = TIMERCHEQUEOTEMPERATURA
    tempMedidor   = TIMERMEDICION
    tempQueue     = TIMERCOLAEVENTOS
    tempPing      = TIMERPING
    tempCheckusb  = TIMECHECKUSBETHERNET 
    tempHora      = TIMECHECK_USB_ETHERNET_TIME
    tempMdfr      = TIMER_MDFR
    
    #threading.Thread(target=awsaccess.iniciar_recepcion_mensajes, daemon=True).start()
 
    # Publicar el encendido del sistema
    util.logging.info("Sistema encendido.")
    # conexion a AWS
    conneced_aws = json.dumps(eventHandler.pyp_Conect())
    # mediciones de los  sensores Modbus RTU 
    datos = obtener_datos_medidores_y_sensor()
    Temp.iniciar_wdt()
    if  util.check_internet_connection():
         # Conectar al cliente MQTT
        mqtt_client = awsaccess.connect_to_mqtt()
        if mqtt_client:
                                        
            awsaccess.publish_mediciones(mqtt_client, conneced_aws)
            awsaccess.publish_mediciones(mqtt_client, datos['sensor_CT01CO2'])
            awsaccess.publish_mediciones(mqtt_client, datos['sensor_THT03R'])
            awsaccess.disconnect_from_aws_iot(mqtt_client)
            
            
        else:
            # Hay internet, pero falla conectar MQTT:
            util.logging.error("No hay Conexion a AWS, almacena en la cola, sensor_CT01CO2, sensor_THT03R y conneced_aws.")
            fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
            fileventqueue.agregar_evento(datos['sensor_THT03R'])
            fileventqueue.agregar_evento(conneced_aws)
             
    else:
        # No hay internet:
        util.logging.error("No hay internet, almacena en la cola,sensor_CT01CO2, sensor_THT03R y conneced_aws.")
        fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
        fileventqueue.agregar_evento(datos['sensor_THT03R'])
        fileventqueue.agregar_evento(conneced_aws)
        
    # Verificar la temperatura al inicio
    Temp.check_temp()
    # Bucle principal
    contador_envio = 0  # Inicialízalo fuera del loop principal
    while True:
        tempRaspberry, tempMedidor, tempQueue, tempPing, tempCheckusb, tempMdfr = util.actualizar_temporizadores(
        tempRaspberry, tempMedidor, tempQueue, tempPing, tempCheckusb, tempMdfr)
        
        if tempRaspberry == 0:
            tempRaspberry = TIMERCHEQUEOTEMPERATURA
            json_estado = util.payload_estado_sistema_y_medidor()
            Sistema =json.dumps(json_estado)
            #se inicia el wdt 
            Temp.iniciar_wdt()
        # lógica normal de envío cada 3 ciclos
            contador_envio += 1
            if contador_envio >= 3:
                contador_envio = 0  # Reiniciar después de enviar
                if  util.check_internet_connection():
                    mqtt_client = awsaccess.connect_to_mqtt()
                    if mqtt_client:
                        awsaccess.publish_mediciones(mqtt_client, Sistema)
                        awsaccess.disconnect_from_aws_iot(mqtt_client)
                else:
                    fileventqueue.agregar_evento(Sistema)
             
        # Mediciones cada 1 minutos
        if tempMdfr == 0:
            tempMdfr = TIMER_MDFR
            # mediciones de los Co2 (ct01) Hum Temp (tht03r)
            datos = obtener_datos_medidores_y_sensor()
             # --- EXTRAER CO2 Y CONTROLAR RELÉS ---
            try:
                cfg = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml')
                ctl = cfg.get('medidores', {}).get('ct01co2_sensor', {}).get('control', {})
                CO2_LOW  = int(ctl.get('co2_ppm_low'))
                CO2_HIGH = int(ctl.get('co2_ppm_high'))
                
                # --- EXTRAER CO2 Y CONTROLAR RELÉS ---
                payload = datos.get('sensor_CT01CO2')  # tu clave actual
                evt = json.loads(payload) if isinstance(payload, str) else payload
                co2_ppm = int(float(evt['d'][0]['v'][0]))  # v[0] = CO2 en ppm

                util.logging.info(f"CO2 ppm={co2_ppm} (low={CO2_LOW}, high={CO2_HIGH})")
            

                if co2_ppm <= CO2_LOW:
                # Debajo de 5000 → enciende relé1 (GPIO10), apaga relé2
                    Temp.setgas(True)
                    Temp.setextractor(False)
                    
                elif co2_ppm >= CO2_HIGH:
                    # Encima de 10000 → enciende relé2 (GPIO9), apaga relé1
                    Temp.setgas(False)
                    Temp.setextractor(True)
                   
                   
               
            except Exception as e:
                util.logging.error(f"No se pudo procesar CO2 para relés: {e}")
        
        # Mediciones cada 10 minutos
        if tempMedidor == 0:
            tempMedidor = TIMERMEDICION
            # datos de los sensores
            datos = obtener_datos_medidores_y_sensor()
            
            if  util.check_internet_connection():
                mqtt_client = awsaccess.connect_to_mqtt()
                if mqtt_client:
                    awsaccess.publish_mediciones(mqtt_client,datos['sensor_CT01CO2'])
                    awsaccess.disconnect_from_aws_iot(mqtt_client)
                   
                else:
                    # Hay internet, pero falla conectar MQTT:
                    fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
                    
            else:
                # No hay internet:
                fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
                
        if tempQueue == 0:
            tempQueue = TIMERCOLAEVENTOS
            process_event_queue()
'''
        if tempPing == 0:
            interfaz = "eth0"
            tempPing = TIMERPING
            util.run_in_thread(interfaz)
            #if util.enable_interface(interfaz):
                #util.logging.info(f"Conexión a internet disponible en {interfaz}.")
            #else:
                #util.logging.info(f"Sin conexión a internet en {interfaz}.")    
            

        if tempCheckusb == 0:
            tempCheckusb = TIMECHECKUSBETHERNET
            tempHora -= 1
            if tempHora == 0:
                tempHora = TIMECHECK_USB_ETHERNET_TIME
                util.check_usb_connection()
                
    
        #with shared.mensaje_lock:
        #    if shared.mensaje_recibido:
        #        mensaje = shared.mensaje_recibido
        #        shared.mensaje_recibido = None
        #        try:
        #            data = json.loads(mensaje)
        #            comando_mensaje = data.get("message", "")
        #            util.logging.warning("Msj MQTT: "+ comando_mensaje )
        #            
        #            if comando_mensaje == "disconnect":
               #         tunel_watcher.cerrar_tunel()
        #                util.logging.info("Túnel cerrado correctamente.")
        #                
        #            elif comando_mensaje.startswith("connect|"):
        #          #      ip = comando_mensaje.split("|")[1]
        #           #     tunel_watcher.set_destino(ip)
        #            #    tunel_watcher.run_ssh()
        #                util.logging.info(f"msj mqtt ...")
        #            else:
        
        #               util.logging.warning(f"Comando no reconocido: {comando_mensaje}")
        #        except Exception as e:
        #            util.logging.error(f"Error al procesar el mensaje MQTT: {e}")
'''
# Punto de entrada principal
if __name__ == '__main__':
    main_loop()
