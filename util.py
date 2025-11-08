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
    
def ensure_internet_failover():
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
 
    try:
        current_route = os.popen("ip route show default").read()
        if "default via" in current_route and active_interface in current_route:
            logging.info(f"La ruta predeterminada ya está en {active_interface}.")
            return False
        os.system("sudo ip route del default 2>/dev/null")
        # no pongas 'via' si el DHCP ya la creó; deja que el kernel la resuelva
        os.system(f"sudo ip route add default dev {active_interface}")
        restaurar_dns()
        logging.info(f"Ruta predeterminada cambiada a {active_interface}")
        return True
    except Exception as e:
        logging.error(f"Error al cambiar la ruta a {active_interface}: {e}")
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
    
    try:
        ifconfig_output = subprocess.check_output(["ip", "addr", "show", "usb0"], text=True)
        if "usb0:" in ifconfig_output:
            logging.info("'usb0' detectado. Renovando DHCP con dhcpcd…")
            # fuerza DHCP y rutas para usb0
            subprocess.run(["sudo", "dhcpcd", "-n", "usb0"], check=False)
            # si no hay default via, intenta poner el gateway común del SIM7600
            route = subprocess.check_output(["ip", "route"], text=True)
            if "default via" not in route:
                logging.warning("No hay 'default via' tras dhcpcd; intentando 192.168.225.1…")
                subprocess.run(["sudo", "ip", "route", "add", "default", "via", "192.168.225.1", "dev", "usb0"], check=False)
        else:
            logging.warning("'usb0' no está presente.")
    except Exception as e:
        logging.error(f"Error al revisar/renovar usb0: {e}")

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
        addrs = psutil.net_if_addrs().get(iface, [])
        for a in addrs:
            if a.family == socket.AF_INET:
                return a.address
        return None
    except Exception:
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
                logging.warning("No hay IP en usb0: reset de la interfaz usb0")
                reset_usb0()
                usb_ip = iface_ip4(usb_iface) or ""
                ip_activa = usb_ip
                if not ip_activa:
                    logging.error("usb0 sigue sin IP después del reset")
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
    try:
        # Ejecutar dhclient en la interfaz usb0
        subprocess.run(
            ["sudo", "dhclient", "-v", "usb0"],
            check=True
        )
        # Consultar la IP obtenida en usb0
        ip_result = subprocess.run(
            ["ip", "addr", "show", "usb0"],
            capture_output=True,
            text=True
        )
        for line in ip_result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                ip_con_mask = line.split()[1]  # Ejemplo: "192.168.1.45/24"
                ip = ip_con_mask.split("/")[0]  # Solo la IP -> "192.168.1.45"
                logging.info(f"Renovar Dirección IP obtenida en usb0: {ip}")
                
                return ip

        logging.warning("No se encontró dirección IP en usb0")
        return None

    except subprocess.CalledProcessError:
        logging.warning("Error al ejecutar dhclient")
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
