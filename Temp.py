import subprocess
import time, json
import RPi.GPIO as GPIO
import util
import threading
import signal
import modbusdevices, awsaccess, fileventqueue, modbusdevices


RELAY_YAML = '/home/pi/.scr/.scr/RPI-MDFR/device/relayDioustou-4.yml'
RELAY_KEY  = 'relayDioustou_4r'
# constantes de programa
FORMATO_DATE="%d/%m/%Y %H:%M "
GPIO11_VENTILADOR=11 #11 18
GPIO5_PILOTO=5 #5 22
GPIO23_WDI=23
GPIO09_RELE2_SIRENA=9
GPIO10_RELE1_BALIZA=10

# Pines fijos del HAT
DOOR_PIN_BCM = 13          # Puerta (entrada)
MAN_BUTTON_PIN_BCM = 6
#Definiciones de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(GPIO11_VENTILADOR, GPIO.OUT)
GPIO.setup(GPIO5_PILOTO, GPIO.OUT)
GPIO.setup(GPIO23_WDI, GPIO.OUT)
GPIO.setup(GPIO09_RELE2_SIRENA, GPIO.OUT)
GPIO.setup(GPIO10_RELE1_BALIZA, GPIO.OUT)


# Estado interno puerta
_door_state = {
    "active": None,          # True=abierta (con invert_active_low=True)
    "changed_ts": None,      # time.monotonic() del último cambio
}
_man_state = {
    "latched": False,       # True si sirena/baliza ON esperando que se abra la puerta
    "pressed_ts": None,     # instante (monotonic) del último PRESSED
    "last_pressed": False,   # estado lógico previo (True=presionado)
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

#-----------------------------------------------------------------------------------------------------------
#Informa la configuración de los relays lee el YAML
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
    return ok

#-----------------------------------------------------------------------------------------------------------
#rele extractor abre una ventana
#-----------------------------------------------------------------------------------------------------------
def setextractor(on: bool):
    """Extractor corresponde a RELAY 2 = 'extractor'."""
    cfg = _cfg_relays()
    ok = modbusdevices.relay_set(cfg, 'extractor', bool(on))
    return ok
	
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
    cfg = _cfg_relays()
    #util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/relayDioustou-4.yml', 'relayDioustou_4r')
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
	return GPIO.input(GPIO09_RELE2_SIRENA)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)	 
#-----------------------------------------------------------------------------------------------------------
#Informa el estado de la baliza
#-----------------------------------------------------------------------------------------------------------
def getbaliza():
	return GPIO.input(GPIO10_RELE1_BALIZA)  # 1 = cerrada, 0 = abierta (o viceversa según conexión)
#-----------------------------------------------------------------------------------------------------------
#Lee el pin de puerta con inversión
#-----------------------------------------------------------------------------------------------------------
def _door_read_active(invert_low: bool) -> bool:
    """
    Lee el pin de puerta y aplica la inversión:
    - invert_low=True  => activo si GPIO lee 0 (pull-up + contacto a GND)
    - invert_low=False => activo si GPIO lee 1
    """
    raw = GPIO.input(DOOR_PIN_BCM)  # 0/1
    return (raw == 0) if invert_low else (raw == 1)
#-----------------------------------------------------------------------------------------------------------
#Carga configuración de la puerta desde door.yml
#-----------------------------------------------------------------------------------------------------------
def _door_cfg():
    try:
        cfg = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/door.yml')
        return cfg.get('medidores', {}).get('door_sensor', {}) if isinstance(cfg, dict) else {}
    except Exception as e:
        util.logging.error(f"[DOOR] No se pudo cargar door.yml: {e}")
        return {}

#-----------------------------------------------------------------------------------------------------------
# Informa si la puerta está abierta
#-----------------------------------------------------------------------------------------------------------
def door_is_open() -> bool:
    """
    True si la puerta está ABIERTA. Usa inversión definida en door.yml.
    NO publica nada; sólo lectura.
    """
    door = _door_cfg()
    invert = bool(door.get('invert_active_low', True))
    try:
        # Asegura modo/entrada (idempotente)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DOOR_PIN_BCM, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    except Exception:
        pass
    return _door_read_active(invert)
#-----------------------------------------------------------------------------------------------------------
# Busca en registers por alias o name; devuelve u en str.
#-----------------------------------------------------------------------------------------------------------
def _get_unit(regs, candidates, default_str):
    """Busca en registers por alias o name; devuelve u en str."""
    cand = set(candidates)
    for r in regs or []:
        if str(r.get('alias')) in cand or str(r.get('name')) in cand:
            u = r.get('u')
            if u is not None:
                return str(u)
    util.logging.warning(f"[DOOR] u-code no encontrado para {candidates}; usando {default_str}")
    return str(default_str)
#-----------------------------------------------------------------------------------------------------------
# Callback de interrupción de puerta
#-----------------------------------------------------------------------------------------------------------
def _door_callback(channel):
    door = _door_cfg()
    i_value = int(door.get('i', 12))
    regs = door.get('registers', [])
    # usa lo que venga en YAML; defaults: abierta=145, duración=138
    u_open = _get_unit(regs, {"door_open", "estado_puerta"}, "138")
    u_dur  = _get_unit(regs, {"door_open_duration_s", "duracion_abierta"}, "145")

    invert = bool(door.get('invert_active_low', True))
    active = _door_read_active(invert)  # True = abierta
    now = time.monotonic()

    last = _door_state.get("active")
    if last is None:
        _door_state["active"] = active
        _door_state["changed_ts"] = now
        # opcional: publicar estado inicial solo si está abierta
        if active:
            _publish_ivu(i_value, ["1"], [u_open])
        return

    if active == last:
        return

    prev_ts = _door_state["changed_ts"]
    _door_state["active"] = active
    _door_state["changed_ts"] = now

    if active:
        util.logging.warning("[DOOR] ABIERTA → apagar relés Modbus.")
        all_relay()
        #_publish_ivu(i_value, ["1"], [u_open])  # evento “abierta”
        # liberar latch de hombre atrapado
        try:
            if man_state.get("latched"):
                setsirena(False)
                setbaliza(False)
                _man_state["latched"] = False
                _man_state["pressed_ts"] = None
               # _man_state["last_pressed"] = False
                util.logging.info("[MAN] LATCH LIBERADO por apertura de puerta.")
        except Exception as e:
            util.logging.error(f"[MAN] Error al liberar latch: {e}")
        _publish_ivu(i_value, ["1"], [u_open])  # v=1, u=138
        _man_state["last_pressed"] = _btn_read_active(True)  # activo-bajo
    else:
        dur = round(now - prev_ts, 1)
        util.logging.info(f"[DOOR] CERRADA. Abierta {dur}s")
        _publish_ivu(i_value, [str(dur)], [u_dur])  # evento “cerrada” (solo duración)

#-----------------------------------------------------------------------------------------------------------
# Prepara el payload JSON para IVU puerta esta abierta
#-----------------------------------------------------------------------------------------------------------
def _payload_ivu(i_value: int, v_list, u_list):
    v_norm = [(None if v is None else str(v)) for v in v_list]
    u_norm = [(None if u is None else str(u)) for u in u_list]
    return {"d": [{"t": util.get__time_utc(), "i": int(i_value), "v": v_norm, "u": u_norm}]}
#-----------------------------------------------------------------------------------------------------------
# Publica IVU puerta abierta o cerrada
#-----------------------------------------------------------------------------------------------------------
def _publish_ivu(i_value: int, v_list, u_list):
    try:
        msg = json.dumps(_payload_ivu(i_value, v_list, u_list))
        if util.check_internet_connection():
            cli = awsaccess.connect_to_mqtt()
            if cli:
                awsaccess.publish_mediciones(cli, msg)
                awsaccess.disconnect_from_aws_iot(cli)
                util.logging.info(f"[DOOR] Dato enviado (i={i_value}, v={v_list}, u={u_list})")
            else:
                #util.logging.error("[DOOR] MQTT no disponible. Cola local.")
                fileventqueue.agregar_evento(msg)
        else:
            #util.logging.error("[DOOR] Sin internet. Cola local.")
            fileventqueue.agregar_evento(msg)
    except Exception as e:
        util.logging.error(f"[DOOR] Error publicando IVU: {type(e).__name__}: {e}")

#-----------------------------------------------------------------------------------------------------------
#Configura interrupción GPIO de puerta solo una vez
#-----------------------------------------------------------------------------------------------------------
def setup_door_interrupt():
    """
    Configura GPIO13 como entrada con pull-up y registra interrupción BOTH.
    Si add_event_detect falla (pin ya tomado/permisos), activa fallback por polling.
    """
    door = _door_cfg()
    debounce_ms = int(door.get('debounce_ms', 80))
    invert = bool(door.get('invert_active_low', True))

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Limpieza defensiva: quita detección previa y limpia SOLO este pin
    try:
        GPIO.remove_event_detect(DOOR_PIN_BCM)
    except Exception:
        pass
    try:
        GPIO.cleanup(DOOR_PIN_BCM)
    except Exception:
        pass

    # Re-configura y estabiliza
    GPIO.setup(DOOR_PIN_BCM, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    time.sleep(0.02)

    # Inicializa estado
    _door_state["active"] = _door_read_active(invert)
    _door_state["changed_ts"] = time.monotonic()

    # Intenta edge detection
    try:
        GPIO.add_event_detect(
            DOOR_PIN_BCM,
            GPIO.BOTH,
            callback=_door_callback,
            bouncetime=debounce_ms
        )
        util.logging.info(f"[DOOR] Interrupción lista en GPIO{DOOR_PIN_BCM} (debounce={debounce_ms} ms)")
        return
    except RuntimeError as e:
        util.logging.error(f"[DOOR] add_event_detect falló: {e}. Activando fallback por polling…")

    # Fallback por polling (50 ms o el debounce configurado)
    def _door_poll_worker():
        last = _door_state["active"]
        while True:
            cur = _door_read_active(invert)
            if cur != last:
                _door_callback(DOOR_PIN_BCM)  # dispara la misma lógica
                last = cur
            time.sleep(max(0.05, debounce_ms / 1000.0))

    t = threading.Thread(target=_door_poll_worker, daemon=True)
    t.start()
    util.logging.info("[DOOR] Fallback por polling activado.")
#-----------------------------------------------------------------------------------------------------------
#lee la configuración del botón hombre atrapado
#-----------------------------------------------------------------------------------------------------------   
def _btn_cfg():
    try:
        cfg = util.cargar_configuracion('/home/pi/.scr/.scr/RPI-MDFR/device/door.yml')
        return cfg.get('medidores', {}).get('man_trapped', {}) if isinstance(cfg, dict) else {}
    except Exception:
        return {}
#-----------------------------------------------------------------------------------------------------------
# Lee el pin del botón hombre atrapado con inversión
#-----------------------------------------------------------------------------------------------------------
def _btn_read_active(invert_low: bool) -> bool:
    """True si PRESIONADO."""
    raw = GPIO.input(MAN_BUTTON_PIN_BCM)  # 0/1
    return (raw == 0) if invert_low else (raw == 1)
#-----------------------------------------------------------------------------------------------------------
# Callback de interrupción de botón hombre atrapado
#-----------------------------------------------------------------------------------------------------------
def _man_button_callback(channel):
    cfg = _btn_cfg()
    i_value = int(cfg.get('i', 12))
    regs = cfg.get('registers', [])
    u_pressed = _get_unit(regs, {"man_pressed"}, "310")
    
    #invert = bool(cfg.get('invert_active_low', False))

    # Espera corta y re-lee para asegurarse que sigue en 0 (activo-bajo)
    #time.sleep(0.02)  # 20 ms
    if not _btn_read_active(invert):     # debe seguir en 1
        return
    
    # Ya latcheado => no repetir
    
    if _man_state["latched"]:
        util.logging.info("[MAN] Botón presionado pero ya estaba latcheado; sin cambio.")
        return

    # LATCH: enciende sirena & baliza y guarda TS
    setsirena(True)
    setbaliza(True)
    _man_state["latched"] = True
    _man_state["pressed_ts"] = time.monotonic()
    #_man_state["last_pressed"] = True  # estado actual
    util.logging.warning("[MAN] LATCH ACTIVO → sirena y baliza ON (esperando apertura de puerta).")

    # Publicación: evento PRESSED (v=1, u=310)
    _publish_ivu(i_value, ["1"], [u_pressed])
#-----------------------------------------------------------------------------------------------------------
# Configura interrupción GPIO de botón hombre atrapado solo una vez
#-----------------------------------------------------------------------------------------------------------
def setup_man_button_interrupt():
    cfg = _btn_cfg()
    debounce_ms = int(cfg.get('debounce_ms', 80))
    #invert = bool(cfg.get('invert_active_low', True))  # true = activo-bajo
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    

    try: GPIO.remove_event_detect(MAN_BUTTON_PIN_BCM)
    except Exception: pass
    try: GPIO.cleanup(MAN_BUTTON_PIN_BCM)
    except Exception: pass
    
    # Pull-up interno: reposo en 1; al presionar baja a 0
    GPIO.setup(MAN_BUTTON_PIN_BCM, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    time.sleep(0.02)

   # Estado inicial (no dispares si ya entra en 0 por wiring/ruido)
    _man_state["latched"] = False
    _man_state["pressed_ts"] = None
    #_man_state["last_pressed"] = False

    try:
        # Solo flanco de bajada (HIGH->LOW) coherente con activo-bajo
        GPIO.add_event_detect(
            MAN_BUTTON_PIN_BCM,
             GPIO.RISING,
            callback=_man_button_callback,
            bouncetime=debounce_ms
        )
        util.logging.info(f"[MAN] IRQ FALLING GPIO{MAN_BUTTON_PIN_BCM} (debounce={debounce_ms} ms)")
    except RuntimeError as e:
        util.logging.error(f"[MAN] add_event_detect falló: {e}. Activando polling…")
        def _poll():
            #last = _btn_read_active(invert)
            last = GPIO.input(MAN_BUTTON_PIN_BCM)  # 1 reposo, 0 presionado
            while True:
                #cur = _btn_read_active(invert)
                cur = GPIO.input(MAN_BUTTON_PIN_BCM)  # 1 reposo, 0 presionado
                # Dispara al detectar transición 1->0 (activo-bajo)
                if last == 0 and cur == 1:         # flanco 1->0
                    _man_button_callback(MAN_BUTTON_PIN_BCM)
                last = cur
                time.sleep(max(0.05, debounce_ms / 1000.0))
        threading.Thread(target=_poll, daemon=True).start()
