# Función para registrar eventos en un archivo
import datetime
import logging
import psutil
import os
import subprocess
import time
import sys
import socket
import threading
import yaml
import Temp
import json
import shlex, pathlib
# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Nivel mínimo de los mensajes que se registrarán
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato del mensaje
    handlers=[
        logging.FileHandler("app.log"),  # Guardar en un archivo log
        logging.StreamHandler()  # Mostrar en la consola
    ]
)
ruta ="/home/pi/.scr/.scr/RPI-MDFR/log_eventos.txt"
# ---- Estado para control de reinicios en usb0 (cooldowns) ----


_USB_GUARD = {
    "last_dhcp": 0.0,     # último intento de DHCP (s)
    "last_pdp": 0.0,      # último intento de PDP/ECM (s)
    "last_rebind": 0.0,   # último unbind/bind (s)
    "fails": 0,           # fallas consecutivas
}

# Enfriamientos (ajústalos si quieres)
CD_DHCP   = 30.0     # segundos entre dhcpcd -n usb0
CD_PDP    = 90.0     # segundos entre secuencias AT
CD_REBIND = 180.0    # segundos entre unbind/bind USB

def _now(): return time.monotonic()

def _usb0_ip_quiet():
    """Devuelve la IPv4 de usb0 (o None) sin tocar DHCP."""
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "dev", "usb0"],
            text=True
        )
        # líneas tipo: '5: usb0    inet 192.168.225.21/24 brd 192.168.225.255 scope global ...'
        for token in out.split():
            if '/' in token and token.count('.') == 3:
                return token.split('/')[0]
    except Exception:
        pass
    return None


def _has_net_iface(iface, host="1.1.1.1", timeout=2):
    return subprocess.call(
        ["ping", "-I", iface, "-c", "1", f"-W{timeout}", host],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ) == 0

def _has_net_any():
    """Verdadero si hay salida a Internet por cualquier interfaz."""
    return subprocess.call(
        ["ping", "-c", "1", "-W", "2", "1.1.1.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ) == 0

def _default_is_usb0():
    try:
        s = subprocess.check_output(["ip", "route", "show", "default"], text=True)
        return " dev usb0" in s
    except Exception:
        return False

def _set_default_if_missing_for_usb0():
    """
    Si no hay default via usb0, intenta aprenderla; si no, usa gateway ECM.
    Usa 'replace' y metric 150. Nunca 1.1.1.1.
    """
    try:
        s = subprocess.check_output(["ip", "route"], text=True)
        for line in s.splitlines():
            if line.startswith("default ") and " dev usb0 " in line:
                return True
    except Exception:
        pass

    # aprender via real
    try:
        s = subprocess.check_output(["ip", "route", "show", "dev", "usb0"], text=True)
        for line in s.splitlines():
            if line.startswith("default ") and " via " in line:
                gw = line.split()[2]
                return subprocess.call(
                    ["sudo","ip","route","replace","default","via",gw,"dev","usb0","metric","150"]
                ) == 0
    except Exception:
        pass

    # heurística ECM correcta
    for gw in ("192.168.225.1", "192.168.100.1"):
        if subprocess.call(
            ["sudo","ip","route","replace","default","via",gw,"dev","usb0","metric","150"]
        ) == 0:
            return True
    return False



#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def log_event(message):
    try:
        with open(ruta, "a") as log_file:
            # Registrar la fecha y hora actual
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Escribir el mensaje en el archivo
            log_file.write(f"[{current_time}] {message}\n")
    except Exception as e:
        print(f"Error al escribir en el archivo log_eventos: {e}")
        

#-----------------------------------------------------------------------------------------------------------
# Función para obtener el tiempo UTC en formato timestamp
#-----------------------------------------------------------------------------------------------------------
def get__time_utc():
    now = datetime.datetime.now()
    timestamp = datetime.datetime.timestamp(now)
    return str(int(timestamp))
#
def signal_handler(sig, frame):
    sys.exit(0)


def check_internet_connection():
    try:
        # Definición de parámetros
        hostname = "google.com"
        interfaces = {"eth0": "Ethernet", "usb0": "USB"}

        # Intento de conexión en cada interfaz
        for interface, name in interfaces.items():
            response = os.system(f"ping -I {interface} -c 1 {hostname} > /dev/null 2>&1")
            if response == 0:
                # Si hay conexión en la interfaz actual, cambiar la ruta predeterminada
                if switch_default_route_to(interface):
                    logging.info(f"Internet: Conectado a través de {name}")
                return True

        # Si ninguna interfaz tiene conexión
        logging.warning("Internet: No hay conexión en ninguna interfaz.")
        renovar_ip_usb0()
        return False

    except Exception as e:
        logging.error(f"Error al intentar verificar la conexión: {e}")
        return False
    
def _internet_failoverensure():
    """
    Prioridad: eth0 > usb0.
    - Si eth0 tiene Internet, deja default por eth0.
    - Si no, intenta usb0: renueva DHCP, pone gateway si falta y cambia default.
    Devuelve True si hay Internet por alguna.
    """
    try:
        # 1) ¿Hay internet por ETH?
        if os.system("ping -I eth0 -c 1 -W 2 1.1.1.1 > /dev/null 2>&1") == 0:
            switch_default_route_to("eth0")
            logging.info("Failover: usando Ethernet (eth0).")
            return True

        logging.warning("ETH sin salida. Probando USB (SIM7600)…")

        # 2) Intentar levantar usb0
        check_usb_connection()  # dhcpcd -n usb0 + default via 192.168.225.1 si falta

        # 3) ¿Ya hay default por usb0?
        route = os.popen("ip route").read()
        if "default via" in route and "usb0" in route:
            # prueba IP y DNS
            if os.system("ping -I usb0 -c 1 -W 2 1.1.1.1 > /dev/null 2>&1") == 0:
                restaurar_dns()  # 8.8.8.8 / 8.8.4.4
                logging.info("Failover: usando módem 4G (usb0).")
                return True

        logging.error("Sin salida por eth0 ni usb0 (tras intento de recuperación).")
        return False

    except Exception as e:
        logging.error(f"ensure_internet_failover() fallo: {e}")
        return False

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------    
def switch_default_route_to(active_interface):
 

    """
    Cambia la ruta por defecto al dispositivo dado sin bajar otras interfaces.
    """
    try:
        current_route = os.popen("ip route show default").read()
        if "default via" in current_route and active_interface in current_route:
            logging.info(f"La ruta predeterminada ya está en {active_interface}.")
            return False
        # limpia default y pone por dispositivo (el GW lo aporta dhcpcd)
        os.system("sudo ip route del default 2>/dev/null")
        cmd = f"sudo ip route add default dev {active_interface}"
        os.system(cmd)
        restaurar_dns()
        logging.info(f"Ruta predeterminada cambiada a {active_interface}")
        return True
    except Exception as e:
        logging.error(f"Error al cambiar ruta a {active_interface}: {e}")
        return False



def _run(cmd, check=False):
    return subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=check)

def _iface_up(iface):
    r = _run(f"ip link show {iface}")
    return r.returncode == 0 and "state UP" in r.stdout

def _has_net(iface=None, host="1.1.1.1", timeout=2):
    cmd = f"ping -c1 -W{timeout} {host}"
    if iface: cmd = f"ping -I {iface} -c1 -W{timeout} {host}"
    return _run(cmd).returncode == 0

def _gw_for_iface(iface):
    r = _run("ip route").stdout
    for line in r.splitlines():
        if line.startswith("default ") and f" dev {iface} " in line:
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via")+1]
    # vecino .1 como heurística
    r = _run(f"ip neigh show dev {iface}").stdout.splitlines()
    for line in r:
        ip = line.split()[0]
        if ip.endswith(".1"):
            return ip
    return None

def _set_default_via(gw, iface, metric=None):
    os.system("sudo ip route del default 2>/dev/null")
    cmd = f"sudo ip route add default via {gw} dev {iface}"
    if metric is not None: cmd += f" metric {metric}"
    return _run(cmd).returncode == 0

def heal_usb0():
    """
    Mantiene usb0 estable:
      - Si ya hay Internet (por cualquier interfaz) o usb0 tiene IP+ping, NO toca nada.
      - Si falla, repara por escalones con cooldowns: DHCP → PDP/ECM → rebind.
    """
    try:
        # ✅ Si hay Internet por cualquier interfaz, no resetees nada
        if _has_net_any():
            _USB_GUARD["fails"] = 0
            return True

        # ✅ Si usb0 tiene IP y ping, no lo toques
        ip_now = _usb0_ip_quiet()
        if ip_now and _has_net_iface("usb0"):
            _USB_GUARD["fails"] = 0
            return True

        # --- A) DHCP/route (cooldown) ---
        if _now() - _USB_GUARD["last_dhcp"] >= CD_DHCP:
            _USB_GUARD["last_dhcp"] = _now()
            try:
                check_usb_connection()
            except Exception:
                pass
            time.sleep(1.0)  # debounce
            ip_now = _usb0_ip_quiet()
            if not _default_is_usb0():
                _set_default_if_missing_for_usb0()
            if ip_now and _has_net_iface("usb0"):
                _USB_GUARD["fails"] = 0
                restaurar_dns()
                logging.info(f"usb0 OK (IP {ip_now}) tras DHCP/route.")
                return True

        # --- B) PDP/ECM por AT (cooldown) ---
        if _now() - _USB_GUARD["last_pdp"] >= CD_PDP:
            _USB_GUARD["last_pdp"] = _now()
            logging.warning("usb0 sin salida; reactivando PDP/ECM por AT …")
            for tty in ("/dev/ttyUSB2", "/dev/ttyUSB3"):
                if os.path.exists(tty):
                    try:
                        with open(tty, "wb", buffering=0) as f:
                            for cmd in (
                                b"AT\r",
                                b"AT+CFUN=1\r",
                                b'AT+CGDCONT=1,"IP","internet.comcel.com"\r',
                                b'AT+CGAUTH=1,1,"claro","claro"\r',
                                b"AT+CGACT=1,1\r",
                                b"AT+CUSBPIDSWITCH=9011,1,1\r",
                            ):
                                f.write(cmd); time.sleep(0.3)
                        break
                    except Exception as e:
                        logging.debug(f"AT por {tty} fallo: {e}")
            time.sleep(8)
            try:
                check_usb_connection()
            except Exception:
                pass
            if not _default_is_usb0():
                _set_default_if_missing_for_usb0()
            if _usb0_ip_quiet() and _has_net_iface("usb0"):
                _USB_GUARD["fails"] = 0
                restaurar_dns()
                logging.info("usb0 volvió tras PDP/ECM.")
                return True

        # --- C) Re-enumeración USB (cooldown) ---
        if _now() - _USB_GUARD["last_rebind"] >= CD_REBIND:
            _USB_GUARD["last_rebind"] = _now()
            try:
                dev = pathlib.Path("/sys/class/net/usb0")
                if dev.exists():
                    bus = os.path.basename(os.path.realpath(dev / "device"))  # ej. "1-1.2"
                    unbind = "/sys/bus/usb/drivers/usb/unbind"
                    bind   = "/sys/bus/usb/drivers/usb/bind"
                    os.system(f"echo {bus} | sudo tee {unbind} >/dev/null")
                    time.sleep(1.0)
                    os.system(f"echo {bus} | sudo tee {bind} >/dev/null")
                    time.sleep(3.0)
                    try:
                        check_usb_connection()
                    except Exception:
                        pass
                    if not _default_is_usb0():
                        _set_default_if_missing_for_usb0()
                    if _usb0_ip_quiet() and _has_net_iface("usb0"):
                        _USB_GUARD["fails"] = 0
                        restaurar_dns()
                        logging.info("usb0 volvió tras rebind USB.")
                        return True
            except Exception as e:
                logging.warning(f"usb rebind falló: {e}")

        _USB_GUARD["fails"] = min(_USB_GUARD["fails"] + 1, 1000)
        logging.error("usb0 sigue sin Internet (esperando cooldowns).")
        return False

    except Exception as e:
        logging.error(f"heal_usb0() error: {e}")
        return False

def ensure_internet_failover():
    """
    Prioridad: eth0 > usb0.
    - Si ya hay Internet por cualquier interfaz, no toques rutas.
    - Si eth0 tiene salida, pon default por eth0.
    - Si no, levanta/mantiene usb0 con heal_usb0().
    """
    try:
        if _has_net_any():
            return True
        if _iface_up("eth0") and _has_net_iface("eth0"):
            switch_default_route_to("eth0")
            return True
        ok = heal_usb0()
        if ok and not _default_is_usb0():
            _set_default_if_missing_for_usb0()
        return ok
    except Exception as e:
        logging.error(f"ensure_internet_failover() error: {e}")
        return False

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------    
def reiniciar_puerto_usb(port='/dev/ttyUSB0'):
    try:
        # Matar cualquier proceso que esté usando el puerto
        os.system(f"sudo fuser -k {port}")
        
        # Descargar y volver a cargar el módulo del kernel
        os.system("sudo modprobe -r ftdi_sio")  # Cambia "pl2303" según tu controlador
        time.sleep(1)  # Espera un segundo antes de volver a cargar el módulo
        os.system("sudo modprobe ftdi_sio")  # Cambia "pl2303" según tu controlador
        
        logging.info(f"Puerto {port} reiniciado correctamente.")
    except Exception as e:
        logging.error(f"Error al reiniciar el puerto: {e}")
        
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def restaurar_dns():
    logging.info("Restaurando DNS a 8.8.8.8 y 8.8.4.4")
    # Comando para sobrescribir el archivo resolv.conf con el DNS primario
    comando1 = 'echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf'
    
    # Comando para añadir el DNS secundario al archivo resolv.conf
    comando2 = 'echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf'
    
    # Ejecutar los comandos
    subprocess.run(comando1, shell=True, check=True)
    subprocess.run(comando2, shell=True, check=True)   
# Función para verificar y conectar usb0 si está presente
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def check_usb_connection():
    """
    Si existe usb0, renueva DHCP (dhcpcd -n usb0) y, si falta,
    asegura default vía gateway real de usb0 (o heurística ECM).
    NUNCA usa 1.1.1.1 como gateway.
    """
    try:
        out = subprocess.check_output(["ip", "addr", "show", "usb0"], text=True)
        if "usb0:" not in out:
            logging.warning("'usb0' no está presente.")
            return

        logging.info("'usb0' detectado. Renovando DHCP (dhcpcd -n usb0)…")
        subprocess.run(["sudo", "dhcpcd", "-n", "usb0"], check=False)
        time.sleep(1.0)  # debounce: que dhcpcd termine

        # ¿ya hay default por usb0?
        route = subprocess.check_output(["ip", "route"], text=True)
        if "default " in route and " dev usb0 " in route:
            return  # ya está

        # aprender 'via' real en usb0
        try:
            rdev = subprocess.check_output(["ip", "route", "show", "dev", "usb0"], text=True)
            gw = None
            for line in rdev.splitlines():
                if line.startswith("default ") and " via " in line:
                    gw = line.split()[2]
                    break
            if gw:
                subprocess.run(
                    ["sudo","ip","route","replace","default","via",gw,"dev","usb0","metric","150"],
                    check=False
                )
                return
        except Exception:
            pass

        # heurística típica SIM7600 ECM
        for gw in ("192.168.225.1", "192.168.100.1"):
            if subprocess.call(
                ["sudo","ip","route","replace","default","via",gw,"dev","usb0","metric","150"]
            ) == 0:
                return
    except Exception as e:
        logging.error(f"check_usb_connection() error: {e}")


#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------       
def actualizar_temporizadores(tempRaspberry, tempMedidor, tempQueue, tempPing, tempCheckusb, tempMdfr, sleep_time=1):

    time.sleep(1)
    tempRaspberry -= 1
    tempMedidor -= 1
    tempQueue -= 1
    tempPing -= 1
    tempCheckusb -= 1
    tempMdfr -=1
    return tempRaspberry, tempMedidor, tempQueue, tempPing, tempCheckusb,tempMdfr
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def enable_interface(interface, hostname="google.com"):
    try:
        # Verificar si la interfaz está activa
        interface_status = os.popen(f"ip link show {interface}").read()
        if "state UP" in interface_status:
            logging.info(f"La interfaz {interface} ya está activa.")
        else:
        # Enciende la interfaz
            logging.info(f"Encendiendo la interfaz {interface}...")
            os.system(f"sudo ip link set {interface} up")
        
        # Espera 5 segundos para permitir la reconexión
            time.sleep(5)
        
        # Prueba de conexión a internet a través de la interfaz
        logging.info(f"Verificando conexión en la interfaz {interface}...")
        response = os.system(f"ping -I {interface} -c 1 {hostname} > /dev/null 2>&1")
        
        # Verificar si hay conexión
        if response == 0:
            logging.info(f"Conexión a internet detectada en {interface}.")
            return True
        else:
            logging.warning(f"No hay conexión a internet en {interface}.")
            return False
            
    except Exception as e:
        logging.error(f"Error al habilitar o verificar la interfaz {interface}: {e}")
        return False 
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------    
def run_in_thread(interface):
    thread = threading.Thread(target=enable_interface, args=(interface,))
    thread.start()
    return thread
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def cargar_configuracion(path, medidor='meatrolME337'):
    with open(path, 'r') as file:
        config = yaml.safe_load(file)
        #print(config)  # Imprimir la configuración para verificar la estructura
        return config['medidores'].get(medidor, {})
def iface_exists(iface: str) -> bool:
    return os.path.isdir(f"/sys/class/net/{iface}")

def iface_operstate(iface: str) -> str:
    try:
        with open(f"/sys/class/net/{iface}/operstate", "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

def iface_ip4(iface: str) -> str | None:
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "dev", iface],
            text=True
        )
        for tok in out.split():
            if tok.count(".") == 3 and "/" in tok:
                return tok.split("/")[0]
    except Exception:
        pass
    return None

def primera_eth_disponible() -> str | None:
    # Prioriza nombres típicos (eth*, en*)
    candidatos = [n for n in psutil.net_if_addrs().keys() if n.startswith(("eth", "en"))]
    for iface in sorted(candidatos):
        if iface_exists(iface):
            return iface
    return "eth0" if iface_exists("eth0") else None
#-----------------------------------------------------------------------------------------------------------
#Resetea la interfaz usb0
#-----------------------------------------------------------------------------------------------------------
def reset_usb0():
    """
    Baja y sube la interfaz usb0, o bien libera y renueva DHCP.
    Ajusta el comando según tu distro.
    """
    logging.warning("No hay IP en usb0: reset de la interfaz usb0")
    # Opción 1: down/up
    subprocess.run(["sudo", "ifconfig", "usb0", "down"], check=False)
    time.sleep(1)
    subprocess.run(["sudo", "ifconfig", "usb0", "up"],   check=False)
    # Opción 2: renovar DHCP
    # subprocess.run(["sudo", "dhclient", "-r", "usb0"], check=False)
    # time.sleep(1)
    # subprocess.run(["sudo", "dhclient", "usb0"], check=False)
    time.sleep(5)  # espera a que vuelva a negociar IP
#-----------------------------------------------------------------------------------------------------------
# Función para convertir una IP en número eliminando los puntos
#-----------------------------------------------------------------------------------------------------------
def ip_a_numero(ip:str) -> str:
    """
    Convierte '192.168.0.5' → '19216805'.
    Si ip es None o cadena vacía, devuelve '0'.
    """
    if not ip:
        return "0"
    return "".join(ip.split("."))
#-----------------------------------------------------------------------------------------------------------
#obtener la ip de la interfaz usb0
#-----------------------------------------------------------------------------------------------------------    
def obtener_ip_usb0():
    # Obtiene las direcciones de todas las interfaces de red
    interfaces = psutil.net_if_addrs()

    # Verifica si 'usb0' existe en las interfaces
    if 'usb0' in interfaces:
        for info in interfaces['usb0']:
            if info.family == socket.AF_INET:  # Solo IPs IPv4
                return info.address  # Devuelve la dirección IP

    return None
#-----------------------------------------------------------------------------------------------------------
#funcion para armar el payload del estado del sistema y de la raspberry pi
#-----------------------------------------------------------------------------------------------------------
def payload_estado_sistema_y_medidor():
    
 

        # === Obtener métricas del sistema ===
    cpu_temp_c = Temp.cpu_temp()
    memoria = psutil.virtual_memory()
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # === PRIORIDAD DE RED: Ethernet > USB ===
    eth_iface = primera_eth_disponible() or "eth0"
    eth_up    = iface_exists(eth_iface) and iface_operstate(eth_iface) == "up"
    eth_ip    = iface_ip4(eth_iface) if eth_up else None

    usb_iface = "usb0"
    usb_exists = iface_exists(usb_iface)
    usb_up     = usb_exists and iface_operstate(usb_iface) == "up"
    usb_ip     = iface_ip4(usb_iface) if usb_up else None

    # IP activa: si hay Ethernet operativa, usarla; si no, USB (si existe)
    if eth_up and eth_ip:
        ip_activa = eth_ip
        # NO tocar usb0 ni sacar warnings de usb0
    else:
        if usb_exists:
            if usb_ip:
                ip_activa = usb_ip
            else:
                logging.warning("usb0 presente pero sin IP (no se fuerza reset desde payload).")
                #reset_usb0()
                #usb_ip = iface_ip4(usb_iface) or ""
                #ip_activa = usb_ip
                ip_activa = ""
        else:
            logging.info("Interfaz usb0 no existe; sin conexión USB.")
            ip_activa = ""

    # También reportamos IP de Ethernet (aunque no sea la activa)
    ip_eth_report = eth_ip or ""

    ip_sin_puntos = ip_a_numero(ip_activa)     # unidad 137 (IP activa numérica)
    ip_eth_num    = ip_a_numero(ip_eth_report) # unidad 144 (IP Ethernet numérica)
    
     
    # Leer estado de la puerta
    #door_state = Temp.door()
    # Convertir a texto legible
    #door_status_text = "Cerrada" if door_state == 1 else "Abierta"
    # === Armar lista de valores mensurados ===
    mensurados = [
        str(round(cpu_temp_c, 1)), 
        str(memoria.percent),
        str(cpu_usage),
        ip_sin_puntos,
        ip_eth_num   
        #str(door_state)
        ]
    
    Temp.check_temp()
    
    # Cargar unidades y g desde el YAML (como ya venías haciendo)
    cfg = cargar_configuracion(
                '/home/pi/.scr/.scr/RPI-MDFR/device/sistema.yml',
                'variables_del_sistema'
            )
    g_id = cfg.get('id_device')
    unidades_cfg = cfg.get('unidades', [])
    codigos_unidades = [u['codigo'] for u in unidades_cfg]
    #logging.info(f"Estado puerta (GPIO6): {door_status_text}")
    
    logging.info(f"SISTEMA (g={g_id}) → Temp={cpu_temp_c:.1f}°C | RAM={memoria.percent}% | CPU={cpu_usage}% | IP_USB0={ip_activa}| IP_Ethernet={ip_eth_report}")

    # === Construir payload ===
    estado_sistema = {
                    "t": get__time_utc(),
                    "g": g_id,
                    "v": mensurados,
                    "u": codigos_unidades  # 1 = °C, 2 = %RAM
                }
    # Retorno doble: el JSON y el estado de la puerta
    return { "d": [estado_sistema] }
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def renovar_ip_usb0():
    """
    Renueva IP de usb0 con dhcpcd y devuelve la IP IPv4 (o None).
    """
    try:
        subprocess.run(["sudo", "dhcpcd", "-n", "usb0"], check=False)
        ip_result = subprocess.run(["ip", "addr", "show", "usb0"], capture_output=True, text=True)
        for line in ip_result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                ip = line.split()[1].split("/")[0]
                logging.info(f"IP en usb0: {ip}")
                return ip
        logging.warning("No se encontró IP en usb0")
        return None
    except Exception as e:
        logging.warning(f"renovar_ip_usb0() error: {e}")
        return None

    


def _normalize_payload(p):
    """
    Acepta dict o str (JSON) o None, y devuelve dict con key 'd': [ ... ].
    Si no trae 'd', devuelve {}.
    """
    if p is None:
        return {}
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except Exception:
            return {}
    if not isinstance(p, dict):
        return {}
    d = p.get("d")
    if isinstance(d, list):
        return {"d": d}
    return {}

def merge_payloads(*payloads):
    """
    Une varios payloads tipo {"d":[{...}, ...]} en UNO SOLO.
    Ignora None/strings inválidos. Devuelve {"d": [...]}. Si todo está vacío, devuelve {"d": []}.
    """
    merged = []
    for p in payloads:
        norm = _normalize_payload(p)
        dl = norm.get("d", [])
        if isinstance(dl, list):
            merged.extend(dl)
    return {"d": merged}
