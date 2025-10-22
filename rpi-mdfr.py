from dotenv import load_dotenv
import os
import minimalmodbus
import serial
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
#import tunel_watcher

'''
Parametros del pto serie modbus
'''
serialPort= "/dev/ttyS0"

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

#-----------------------------------------------------------------------------------------------------------        
def leer_float32(instrumento, address):
    registros = instrumento.read_registers(address, 2, functioncode=3)
    return struct.unpack(">f", struct.pack(">HH", registros[0], registros[1]))[0]
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def payload_event_CT01CO2(config):
    valores = []
    unidades = []
    try:
        instrumento = minimalmodbus.Instrument(serialPort, config['slave_id'])
        instrumento.serial.baudrate = config['baudrate']
        instrumento.serial.bytesize = config['bytesize']
        instrumento.serial.stopbits = config['stopbits']
        instrumento.serial.timeout = config['timeout']
        instrumento.mode = minimalmodbus.MODE_RTU
        instrumento.clear_buffers_before_each_transaction = True
         # Interpretar la paridad desde el YAML (N, E, O)
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD
        }
        instrumento.serial.parity = parity_map.get(config['parity'].upper(), serial.PARITY_NONE)
     # Leer cada registro del medidor desde la configuración YAML
        for reg in config['registers']:
            val = instrumento.read_register(reg['address'], 0, functioncode=3)
            
            valores.append(str(round(val, 1)))
            unidades.append(str(reg['unit']))
        return {
            "d": [{
                "t": util.get__time_utc(),
                "g": config['id_device'],
                "v": valores,
                "u": unidades
            }]
        }

    except Exception as e:
       util.logging.error(f"Error al leer el ct01co2: {e}")
       return None
   

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def payload_event_THT03R(config):
    """
    Lee temperatura y humedad del sensor THT03R (Modbus RTU) usando la configuración YAML.
    Espera en config:
      - slave_id, baudrate, bytesize, parity, stopbits, timeout
      - opcional: port (si no está, usa variable global serialPort)
      - registers: lista de dicts con:
          { "name": "...", "alias": "...", "address": 0, "unit": 1,
            "fc": 3, "decimals": 1, "signed": false }
    """
    """
    Lee temperatura y humedad del sensor THT03R (Modbus RTU).
    Compatible con tu YAML reducido (sin fc ni decimals definidos).
    """
    valores = []
    unidades = []

    try:
        instrumento = minimalmodbus.Instrument(serialPort, config['slave_id'])
        instrumento.serial.baudrate = config['baudrate']
        instrumento.serial.bytesize = config['bytesize']
        instrumento.serial.stopbits = config['stopbits']
        instrumento.serial.timeout = config['timeout']
        instrumento.mode = minimalmodbus.MODE_RTU
        instrumento.clear_buffers_before_each_transaction = True

        # Paridad
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD
        }
        instrumento.serial.parity = parity_map.get(config['parity'].upper(), serial.PARITY_NONE)

        # Leer cada registro del sensor
        for reg in config['registers']:
            address = reg['address']
            # valores por defecto para este sensor
            fc = 3
            decimals = 1
            signed = False

            val = instrumento.read_register(address, decimals, functioncode=fc, signed=signed)

            # Redondeo suave
            val = round(val, 1)

            valores.append(str(val))
            unidades.append(str(reg['unit']))

        return {
            "d": [{
                "t": util.get__time_utc(),
                "g": config['id_device'],
                "v": valores,
                "u": unidades
            }]
        }

    except Exception as e:
        util.logging.error(f"Error al leer el THT03R: {e}")
        return None
#-----------------------------------------------------------------------------------------------------------
# Función para generar los parámetros del evento
#-----------------------------------------------------------------------------------------------------------
def payload_event(config):
    voltages = []  # Lista para almacenar los valores de voltaje leídos
    units_list = []  # Lista para almacenar las unidades correspondientes
    slave_id = config['slave_id']
    instrumento = minimalmodbus.Instrument(serialPort, slave_id)
    instrumento.serial.baudrate = config['baudrate']
    instrumento.serial.bytesize = config['bytesize']
    instrumento.serial.stopbits = config['stopbits']
    instrumento.serial.timeout = config['timeout']
    instrumento.mode = minimalmodbus.MODE_RTU
    instrumento.clear_buffers_before_each_transaction = True
    
     # Interpretar la paridad desde el YAML (N, E, O)
    parity_map = {
        'N': serial.PARITY_NONE,
        'E': serial.PARITY_EVEN,
        'O': serial.PARITY_ODD
    }
    instrumento.serial.parity = parity_map.get(config['parity'].upper(), serial.PARITY_NONE)
     # Leer cada registro del medidor desde la configuración YAML
    for reg in config['registers']:
        try:
            # Leer el valor flotante de cada registro
            value = leer_float32(instrumento, reg['address'])
            voltages.append(str(round(value, 3)))  # Agregar el voltaje leído a la lista
            units_list.append(str(reg['unit']))  # Agregar la unidad correspondiente a la lista
        except Exception as e:  # Manejo de excepciones
            util.logging.error(f"Error al intentar leer el registro: {reg['address']}: {e}")
            #os.system('sudo reboot')  # Reiniciar si hay error

    # Crear el diccionario con los parámetros del medidor
    key = config['tipo']
    params = {
        "t": util.get__time_utc(),  # Hora en UTC
        key: config['id_device'],  # Identificador o índice
        "v": voltages,  # Lista de voltajes leídos
        "u": units_list  # Lista de unidades
    }
    
    return params
#-----------------------------------------------------------------------------------------------------------
# Función que empaqueta el evento en una estructura JSON
#-----------------------------------------------------------------------------------------------------------
def payloadMedicion(config):
    return {
        "d": [payload_event(config)]  # Contiene los eventos dentro de una lista
    }
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
 
 #-----------------------------------------------------------------------------------------------------------    
def obtener_datos_medidores_y_sensor():
   import json

def obtener_datos_medidores_y_sensor():
    """
    Lee los sensores CT01CO2 y THT03R.
    Si alguno no responde, deja sus valores en None y lo registra en el log.
    Devuelve un diccionario donde cada valor es una cadena JSON.
    """
    try:
        # === SENSOR 1 — CT01CO2 ===
        try:
            config_CT01CO2 = util.cargar_configuracion(
                '/home/pi/.scr/.scr/RPI-MDFR/device/ct01co2.yml',
                'ct01co2_sensor'
            )
            medicion_CT01CO2 = payload_event_CT01CO2(config_CT01CO2)
            if medicion_CT01CO2 is None:
                util.logging.warning("Sensor CT01CO2 no conectado o sin respuesta.")
                medicion_CT01CO2 = {
                    "d": [{"t": util.get__time_utc(), "g": 14, "v": [None], "u": [None]}]
                }
        except Exception as e:
            util.logging.error(f"Error al leer CT01CO2: {e}")
            medicion_CT01CO2 = {
                "d": [{"t": util.get__time_utc(), "g": 14, "v": [None], "u": [None]}]
            }

        medicionSensorCT01CO2 = json.dumps(medicion_CT01CO2)

        # === SENSOR 2 — THT03R ===
        try:
            config_THT03R = util.cargar_configuracion(
                '/home/pi/.scr/.scr/RPI-MDFR/device/tht03r.yml',
                'tht03r_sensor'
            )
            medicion_THT03R = payload_event_THT03R(config_THT03R)
            if medicion_THT03R is None:
                util.logging.warning("Sensor THT03R no conectado o sin respuesta.")
                medicion_THT03R = {
                    "d": [{"t": util.get__time_utc(), "g": 12, "v": [None, None], "u": [None, None]}]
                }
        except Exception as e:
            util.logging.error(f"Error al leer THT03R: {e}")
            medicion_THT03R = {
                "d": [{"t": util.get__time_utc(), "g": 12, "v": [None, None], "u": [None, None]}]
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
    conneced_meter = json.dumps(eventHandler.pyp_Conect())
    # mediciones de los medidores ME337 y el  sensor SHT20
    datos = obtener_datos_medidores_y_sensor()
    Temp.iniciar_wdt()
    if  util.check_internet_connection():
         # Conectar al cliente MQTT
        mqtt_client = awsaccess.connect_to_mqtt()
        if mqtt_client:
                                        
            #awsaccess.publish_mediciones(mqtt_client, conneced_meter)
            awsaccess.publish_mediciones(mqtt_client, datos['sensor_CT01CO2'])
            awsaccess.disconnect_from_aws_iot(mqtt_client)# Mantener la conexión activa y recibir mensajes
            
            
        else:
            # Hay internet, pero falla conectar MQTT:
            util.logging.error("No hay Conexion a AWS, almacena en la cola, las mediciones del medidor, Temp, Humedad y la hora de encendido.")
            fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
            
    else:
        # No hay internet:
        util.logging.error("No hay internet, almacena en la cola, las mediciones del medidor, Temp, Humedad y la hora de encendido.")
        fileventqueue.agregar_evento(datos['sensor_CT01CO2'])
        
    # Verificar la temperatura al inicio
    #Temp.check_temp()
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
            # mediciones de los medidores ME337 y el  sensor SHT20
            datos = obtener_datos_medidores_y_sensor()
             # --- EXTRAER CO2 Y CONTROLAR RELÉS ---
            try:
                payload = datos.get('sensor_CT01CO2')
                # tu rutina suele devolver JSON string; si ya es dict, respeta
                evt = json.loads(payload) if isinstance(payload, str) else payload
                co2_ppm = int(float(evt['d'][0]['v'][0]))  # v[0] = CO2 en ppm

                util.logging.info(f"CO2 ppm={co2_ppm}")

                if co2_ppm <= 1000:
                # Debajo de 5000 → enciende relé1 (GPIO10), apaga relé2
                    Temp.setgas(True)
                    Temp.setextractor(False)
                    
                elif co2_ppm >= 1100:
                    # Encima de 10000 → enciende relé2 (GPIO9), apaga relé1
                    Temp.setgas(False)
                    Temp.setextractor(True)
                   
               
            except Exception as e:
                util.logging.error(f"No se pudo procesar CO2 para relés: {e}")
        
        # Mediciones cada 10 minutos
        if tempMedidor == 0:
            tempMedidor = TIMERMEDICION
              # mediciones de los medidores ME337 y el  sensor SHT20
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

# Punto de entrada principal
if __name__ == '__main__':
    main_loop()
