import subprocess
import time, json
import RPi.GPIO as GPIO
import util
import threading
import signal
import modbusdevices, awsaccess, fileventqueue


RELAY_YAML = '/home/pi/.scr/.scr/RPI-MDFR/device/relayDioustou-4.yml'
RELAY_KEY  = 'relayDioustou_4r'
# constantes de programa
FORMATO_DATE="%d/%m/%Y %H:%M "
GPIO11_VENTILADOR=11 #11 18
GPIO5_PILOTO=5 #5 22
GPIO23_WDI=23
#GPIO6_BOTON=6
#GPIO13_DOOR=13 
GPIO09_RELE2_SIRENA=9
GPIO10_RELE1_BALIZA=10

# Pines fijos del HAT
DOOR_PIN_BCM = 13          # Puerta (entrada)

#Definiciones de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(GPIO11_VENTILADOR, GPIO.OUT)
GPIO.setup(GPIO5_PILOTO, GPIO.OUT)
GPIO.setup(GPIO23_WDI, GPIO.OUT)
GPIO.setup(GPIO09_RELE2_SIRENA, GPIO.OUT)
GPIO.setup(GPIO10_RELE1_BALIZA, GPIO.OUT)

#GPIO.setup(GPIO6_BOTON, GPIO.IN)
#GPIO.setup(GPIO13_DOOR, GPIO.IN)

# Estado interno puerta
_door_state = {
    "active": None,          # True=abierta (con invert_active_low=True)
    "changed_ts": None,      # time.monotonic() del último cambio
}

#######################################
#Mantenimiento raspberry Temperatura
########################################
def cpu_temp():
	thermal_zone = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=subprocess.PIPE)
	out, err = thermal_zone.communicate()
	cpu_temp = int(out.decode())/1000
	return cpu_temp

########################################################
#Se chequea Temperatura y se apaga/prende el ventilador
########################################################
def check_temp():
	cpu = cpu_temp()
	#on_hardware("Temperatura: "+str(cpu))
	if cpu > 48.0  :
		#GPIO.output(GPIO18_VENTILADOR, False)
		GPIO.output(GPIO11_VENTILADOR, True)
		util.logging.info(f"CPU ALTA: {cpu:.1f} ºC")
		
	else: 
		#GPIO.output(GPIO18_VENTILADOR, True)
		GPIO.output(GPIO11_VENTILADOR, False)
		util.logging.info(f"CPU BAJA: {cpu:.1f} ºC")

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------		
# Función para hacer titilar el LED usando PWM
def parpadear_led_500ms():
    GPIO.output(GPIO5_PILOTO, True)
    time.sleep(0.5)  # Mantén el parpadeo durante 500 milisegundos
    GPIO.output(GPIO5_PILOTO, False)
#-----------------------------------------------------------------------------------------------------------
# Función del hilo para el watchdog que da el pulso cada 200 ms
#-----------------------------------------------------------------------------------------------------------  
def wdt():
    util.logging.info("WDT:INICIADO")
    GPIO.output(GPIO23_WDI, True)
    time.sleep(0.2)
    GPIO.output(GPIO23_WDI, False)
    time.sleep(0.2)
#-----------------------------------------------------------------------------------------------------------
#Inicia el watchdog
#-----------------------------------------------------------------------------------------------------------
def iniciar_wdt():
    # Crear y empezar el hilo que ejecutará la función wdt
    hilo_wdt = threading.Thread(target=wdt)
    hilo_wdt.daemon = True  # El hilo se cerrará automáticamente cuando termine el programa principal
    hilo_wdt.start()
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------    
def door():
    return GPIO.input(GPIO6_DOOR)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)
#-----------------------------------------------------------------------------------------------------------
#Informa la configuración de los relays
#-----------------------------------------------------------------------------------------------------------    
def _cfg_relays():
    cfg = util.cargar_configuracion(RELAY_YAML, RELAY_KEY)
    util.logging.info(f"[RELAYS] cfg: dev={cfg.get('device_name')} port={cfg.get('port')} slave={cfg.get('slave_id')}")
    return cfg
#-----------------------------------------------------------------------------------------------------------
# inyecta gas etileno
#-----------------------------------------------------------------------------------------------------------
def setgas(on: bool):
    """Histórico: 'gas' ahora corresponde a RELAY 4 = 'etileno'."""
    cfg = _cfg_relays()
    ok = modbusdevices.relay_set(cfg, 'etileno', bool(on))
    #estados = modbusdevices.relay_read_states(cfg)
    #util.logging.info(f"[RELAYS] setgas({on}) verificación -> etileno={estados.get('etileno')}")
    return ok
	#GPIO.output(GPIO09_RELE2_GAS, estado)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)
#-----------------------------------------------------------------------------------------------------------
#rele extractor abre una ventana
#-----------------------------------------------------------------------------------------------------------
def setextractor(on: bool):
    """Extractor corresponde a RELAY 2 = 'extractor'."""
    cfg = _cfg_relays()
    ok = modbusdevices.relay_set(cfg, 'extractor', bool(on))
    #estados = modbusdevices.relay_read_states(cfg)
    #util.logging.info(f"[RELAYS] setextractor({on}) verificación -> extractor={estados.get('extractor')}")
    return ok
	#GPIO.output(GPIO10_RELE1_EXTRACTOR, estado)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)	
#-----------------------------------------------------------------------------------------------------------
#Rele que activa la recirculacion del aire
#-----------------------------------------------------------------------------------------------------------
def setrecircular(on: bool):
    cfg = _cfg_relays()
    return modbusdevices.relay_set(cfg, 'recircular', bool(on))

#-----------------------------------------------------------------------------------------------------------
#Rele que activa el humidificador
#-----------------------------------------------------------------------------------------------------------
def sethumidificador(on: bool):
    cfg = _cfg_relays()
    return modbusdevices.relay_set(cfg, 'humidificador', bool(on)) 
#-----------------------------------------------------------------------------------------------------------
#Apaga todos los relays
#-----------------------------------------------------------------------------------------------------------
def all_relay():
    cfg = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/relayDioustou-4.yml', 'relayDioustou_4r')
    return modbusdevices.relay_set(cfg, 'all_off')
#-----------------------------------------------------------------------------------------------------------
#Rele interno que activa la sirena 
#-----------------------------------------------------------------------------------------------------------
def setsirena(on:bool):
	GPIO.output(GPIO09_RELE2_SIRENA, bool(on))  # 1 = cerrada, 0 = abierta (o viceversa según conexión)	 
#-----------------------------------------------------------------------------------------------------------
#Rele interno que activa la baliza
#-----------------------------------------------------------------------------------------------------------
def setbaliza(on:bool):
	GPIO.output(GPIO10_RELE1_BALIZA, bool(on))  # 1 = cerrada, 0 = abierta (o viceversa según conexión)	
 
#-----------------------------------------------------------------------------------------------------------
#Informa el estado de los relays
#----------------------------------------------------------------------------------------------------------- 
def relays_estado() -> dict:
    cfg = _cfg_relays()
    return modbusdevices.relay_read_states(cfg)
 
#-----------------------------------------------------------------------------------------------------------
#Informa el estado de la sirena
#-----------------------------------------------------------------------------------------------------------
def getsirena():
	return GPIO.input(GPIO09_SIRENA)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)	 
#-----------------------------------------------------------------------------------------------------------
#Informa el estado de la baliza
#-----------------------------------------------------------------------------------------------------------
def getbaliza():
	return GPIO.input(GPIO10_RELE1_BALIZA)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)
#-----------------------------------------------------------------------------------------------------------
#Carga solo metadatos de la puerta (NO pines).
#-----------------------------------------------------------------------------------------------------------
def _load_door_meta():
    """Carga solo metadatos de la puerta (NO pines)."""
    try:
        m = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/gpio_safety.yml', 'door_meta')
        return m if isinstance(m, dict) else {}
    except Exception as e:
        util.logging.error(f"[DOOR] No se pudo cargar door_meta: {e}")
        return {}
def _door_read_active(invert_active_low: bool) -> bool:
    raw = GPIO.input(DOOR_PIN_BCM)  # 0 o 1
    return (raw == 0) if invert_active_low else (raw == 1)

def _door_callback(channel):
    meta = _load_door_meta()
    gid  = int(meta.get('id_device', 41))
    invert = bool(meta.get('invert_active_low', True))
    u_door = str((meta.get('units') or {}).get('door_state', 300))
    u_dur  = str((meta.get('units') or {}).get('open_duration_s', 301))

    active = _door_read_active(invert)  # True=abierta con invert_active_low=True
    now = time.monotonic()

    last = _door_state.get("active")
    if last is None:
        _door_state["active"] = active
        _door_state["changed_ts"] = now
        # (opcional) emitir estado inicial
        _publish_dgu(_payload_dgu(gid, [1 if active else 0], [u_door]))
        return

    if active == last:
        return  # sin cambio real (rebote ya filtrado por bouncetime)

    _door_state["active"] = active
    prev_ts = _door_state.get("changed_ts", now)
    _door_state["changed_ts"] = now

    if active:
        util.logging.warning("[DOOR] ABIERTA → apagar relés Modbus.")
        all_relay()
        _publish_dgu(_payload_dgu(gid, [1], [u_door]))  # 1=abierta
    else:
        dur = round(now - prev_ts, 1)
        util.logging.info(f"[DOOR] CERRADA. Abierta {dur}s")
        _publish_dgu(_payload_dgu(gid, [0, dur], [u_door, u_dur]))  # 0=cerrada

def _payload_dgu(g: int, v_list, u_list):
    v_norm = [(None if v is None else str(v)) for v in v_list]
    u_norm = [(None if u is None else str(u)) for u in u_list]
    return {"d": [{"t": util.get__time_utc(), "i": g, "v": v_norm, "u": u_norm}]}

def _publish_dgu(payload_dict):
    try:
        msg = json.dumps(payload_dict)
        if util.check_internet_connection():
            cli = awsaccess.connect_to_mqtt()
            if cli:
                awsaccess.publish_mediciones(cli, msg)
                awsaccess.disconnect_from_aws_iot(cli)
                util.logging.info("[DOOR] Alerta enviada a AWS.")
            else:
                util.logging.error("[DOOR] MQTT no disponible. Cola local.")
                fileventqueue.agregar_evento(msg)
        else:
            util.logging.error("[DOOR] Sin internet. Cola local.")
            fileventqueue.agregar_evento(msg)
    except Exception as e:
        util.logging.error(f"[DOOR] Error publicando DGU: {type(e).__name__}: {e}")

def setup_door_interrupt():
    """
    Configura GPIO13 como entrada con pull-up y registra interrupción BOTH.
    Debe llamarse una sola vez al inicio del programa.
    """
    meta = _load_door_meta()
    debounce_ms = int(meta.get('debounce_ms', 80))

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_PIN_BCM, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    try:
        GPIO.remove_event_detect(DOOR_PIN_BCM)
    except Exception:
        pass

    GPIO.add_event_detect(DOOR_PIN_BCM, GPIO.BOTH, callback=_door_callback, bouncetime=debounce_ms)

    # Inicializar estado y (opcional) publicar estado inicial
    invert = bool(meta.get('invert_active_low', True))
    _door_state["active"] = _door_read_active(invert)
    _door_state["changed_ts"] = time.monotonic()
    util.logging.info(f"[DOOR] Interrupción lista en GPIO{DOOR_PIN_BCM} (debounce={debounce_ms} ms)")