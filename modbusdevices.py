import minimalmodbus
import serial
import util  # si usas util.get__time_utc() o logging


'''
Parametros del pto serie modbus
'''
serialPort= "/dev/ttyS0"

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def payload_event_modbus(config):
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
    valores, unidades = [], []
    port = config.get('port', None)
    if port is None:
        port = serialPort
    try:
        #print("\n=== Iniciando lectura THT03R ===")
        #print(f"Puerto: {serialPort}")
        #print(f"Slave ID: {config['slave_id']}")
        #print(f"Baudios: {config['baudrate']}, Paridad: {config['parity']}, Timeout: {config['timeout']}\n")
        instrumento = minimalmodbus.Instrument(port, config['slave_id'])
        instrumento.serial.baudrate = config['baudrate']
        instrumento.serial.bytesize = config['bytesize']
        instrumento.serial.stopbits = config['stopbits']
        instrumento.serial.timeout = config['timeout']
        instrumento.serial.inter_byte_timeout = 0.2
        instrumento.mode = minimalmodbus.MODE_RTU
        instrumento.clear_buffers_before_each_transaction = True
        instrumento.close_port_after_each_call = True
        # Paridad
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD
        }
        instrumento.serial.parity = parity_map.get(config['parity'].upper(), serial.PARITY_NONE)
        # nombre para logs (desde el YAML)
        device_name = config.get('device_name') 

        
        #instrumento.debug = True
        # Leer cada registro del sensor
        for reg in config['registers']:
            address = reg['address']
            # valores por defecto para este sensor
            fc  = reg.get('fc')
            decimals = reg.get('decimals')
            signed = False
            #print(f"→ Leyendo dirección {address} (función {fc}) ...")
             
            val = instrumento.read_register(address, decimals, functioncode=fc, signed=signed)
            #print(f"   Valor leído bruto: {val}")
            
            # Redondeo suave
            val = round(val, 1)

            valores.append(str(val))
            unidades.append(str(reg['unit']))
            #print(f"\nValores finales leídos: {valores}")
            #print(f"Unidades asociadas: {unidades}")
            #print("==============================\n")
        return {
            "d": [{
                "t": util.get__time_utc(),
                "g": config['id_device'],
                "v": valores,
                "u": unidades
            }]
        }

    except Exception as e:
        util.logging.error(f"[{device_name}] Error general al leer el equipo "
            f"(slave={config.get('slave_id')}, port={port}): {type(e).__name__}: {e}")
        return None
    
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def relay_set(config, relay_name: str, on: bool = False) -> bool:
    """
    Enciende/Apaga un relé por nombre usando FC=5 (Write Single Coil).
    relay_name: 'recircular' | 'extractor' | 'humidificador' | 'etileno'
    Soporta:
      - FC5: Write Single Coil
      - FC15: Write Multiple Coils (para all_off)
    """
    try:
        device_name = config.get('device_name') or f"ModbusDevice(g={config.get('id_device')})"
        port = config.get('port', serialPort)
        slave = int(config['slave_id'])

        # buscar el registro por nombre
        reg = next((r for r in config.get('registers', []) if r.get('name') == relay_name), None)
        if not reg:
            util.logging.error(f"[{device_name}] Relay '{relay_name}' no existe en YAML.")
            return False

        addr = int(reg['address'])
        fc   = int(reg.get('fc_write'))
        
        inst = minimalmodbus.Instrument(port, slave)
        inst.serial.baudrate = int(config['baudrate'])
        inst.serial.bytesize = int(config['bytesize'])
        inst.serial.stopbits = int(config['stopbits'])
        inst.serial.timeout  = float(config.get('timeout', 1))
        inst.serial.inter_byte_timeout = float(config.get('inter_byte_timeout', 0))
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = True
        
        
        parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
        inst.serial.parity = parity_map.get(str(config['parity']).upper(), serial.PARITY_NONE)
        
        inst.debug = bool(config.get('debug', False))
        
        # === Modo normal FC5 ===
        if fc == 5:
            inst.write_bit(addr, 1 if on else 0, functioncode=5)
            util.logging.info(f"[{device_name}] FC5 {relay_name} → {'ON' if on else 'OFF'}")
            return True
        # === Modo especial FC15 ===
        elif fc == 15:
            qty = int(reg.get('quantity', 8))
            data_hex = reg.get('data_hex', '00')
            data = bytes.fromhex(data_hex)
            payload = bytes([
                (addr >> 8) & 0xFF, addr & 0xFF,
                (qty >> 8) & 0xFF, qty & 0xFF,
                len(data)
            ]) + data
            inst._perform_command(15, payload)
            util.logging.info(f"[{device_name}] FC15 {relay_name} (addr={addr} qty={qty}) enviado OK")
            return True

        else:
            util.logging.warning(f"[{device_name}] Función no soportada fc_write={fc} para {relay_name}")
            return False

    except Exception as e:
        util.logging.error(f"[{config.get('device_name','Relay')}] Error al escribir relay '{relay_name}': {type(e).__name__}: {e}")
        return False
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------   
def relay_read_states(config) -> dict:
    """
    Lee el estado de todos los relés definidos (FC=1 Read Coils).
    Devuelve dict { name: True/False/None }
    """
    estados = {}
    try:
        device_name = config.get('device_name') or f"ModbusDevice(g={config.get('id_device')})"
        port = config.get('port', serialPort)
        slave = int(config['slave_id'])

        inst = minimalmodbus.Instrument(port, slave)
        inst.serial.baudrate = int(config['baudrate'])
        inst.serial.bytesize = int(config['bytesize'])
        inst.serial.stopbits = int(config['stopbits'])
        inst.serial.timeout  = float(config.get('timeout', 1))
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = True

        parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
        inst.serial.parity = parity_map.get(str(config['parity']).upper(), serial.PARITY_NONE)

        for reg in config.get('registers', []):
            name = reg.get('name')
            addr = int(reg.get('address'))
            try:
                bit = inst.read_bit(addr, functioncode=1)  # FC1: Read Coils
                estados[name] = bool(bit)
            except Exception as e:
                util.logging.warning(f"[{device_name}] No se pudo leer '{name}' (addr={addr}): {type(e).__name__}: {e}")
                estados[name] = None

        util.logging.info(f"[{device_name}] Estados relés: {estados}")
        return estados

    except Exception as e:
        util.logging.error(f"[{config.get('device_name','Relay')}] Error general al leer estados: {type(e).__name__}: {e}")
        return estados
    
    
# modbusdevices.py

def payload_relays_many(config: dict, names: list[str]):
    """
    Lee varios relés por nombre (coils FC1) y arma UN payload IVU:
      - i: config['i'] o config['id_device']
      - v: ["1"/"0"/"None"] por cada relé (orden = names)
      - u: [unidad_por_relé] tomada del YAML (orden = names)
    """
    device_name = config.get('device_name') or f"ModbusDevice(i={config.get('i') or config.get('id_device')})"
    i_value = int(config.get('i', config.get('id_device', 0)) or 0)

    port     = config.get('port', '/dev/ttyS0')
    slave    = int(config.get('slave_id', 1))
    baud     = int(config.get('baudrate', 9600))
    bytesize = int(config.get('bytesize', 8))
    stopbits = int(config.get('stopbits', 1))
    timeout  = float(config.get('timeout', 1))
    parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
    parity  = parity_map.get(str(config.get('parity', 'N')).upper(), serial.PARITY_NONE)

    # Instancia Modbus
    inst = minimalmodbus.Instrument(port, slave)
    inst.serial.baudrate = baud
    inst.serial.bytesize = bytesize
    inst.serial.stopbits = stopbits
    inst.serial.timeout  = timeout
    inst.serial.parity   = parity
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True

    # Índice rápido por nombre
    regs_by_name = {str(r.get('name')): r for r in config.get('registers', [])}

    v_vals, u_vals = [], []
    for name in names:
        reg = regs_by_name.get(name)
        if not reg:
            util.logging.error(f"[{device_name}] Relay '{name}' no existe en YAML.")
            v_vals.append("None")
            u_vals.append("143")  # fallback
            continue

        if str(reg.get('fc_read', '')) != '1':
            util.logging.warning(f"[{device_name}] Relay '{name}' sin fc_read=1; no se puede leer estado.")
            v_vals.append("None")
            u_vals.append(str(reg.get('unit', '143')))
            continue

        addr = int(reg['address'])
        try:
            bit = inst.read_bit(addr, functioncode=1)  # FC1: Read Coils
            v_vals.append("1" if bit else "0")
        except Exception as e:
            util.logging.error(f"[{device_name}] Leer '{name}' addr={addr} falló: {type(e).__name__}: {e}")
            v_vals.append("None")

        u_vals.append(str(reg.get('unit', '143')))

    return {
        "d": [{
            "t": util.get__time_utc(),
            "g": i_value,
            "v": v_vals,
            "u": u_vals
        }]
    }


def payload_relays_from_yaml(yaml_path: str, block_key: str, names: list[str]):
    """
    Atajo: carga el bloque del YAML y llama payload_relays_many().
    """
    cfg = util.cargar_configuracion(yaml_path)
    dev = (cfg or {}).get('medidores', {}).get(block_key)
    if not isinstance(dev, dict):
        raise ValueError(f"Bloque '{block_key}' no existe o YAML inválido.")
    return payload_relays_many(dev, names)

import minimalmodbus, serial, struct, util

def payload_relays_many_packed(config: dict, names: list[str]):
    """
    Lee los coils 0..7 en un solo FC=1 (Read Coils, qty=8) y arma UN payload:
      g = config['id_device'] (o 'i' si no existe)
      v = ["1"/"0"] por cada 'name' (orden dado)
      u = unidad por cada relé, tomada del YAML
    El estado de cada relé se toma del byte de datos: bit=address (0..3).
    """
    device_name = config.get('device_name') or f"ModbusDevice(g={config.get('id_device') or config.get('i')})"
    g_value = int(config.get('id_device', config.get('i', 0)) or 0)

    port     = config.get('port', '/dev/ttyS0')
    slave    = int(config['slave_id'])
    baud     = int(config['baudrate'])
    bytesize = int(config['bytesize'])
    stopbits = int(config['stopbits'])
    timeout  = float(config.get('timeout', 1))
    parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
    parity  = parity_map.get(str(config.get('parity','N')).upper(), serial.PARITY_NONE)

    # índice por nombre
    regs_by_name = {str(r.get('name')): r for r in (config.get('registers') or [])}

    inst = minimalmodbus.Instrument(port, slave)
    inst.serial.baudrate = baud
    inst.serial.bytesize = bytesize
    inst.serial.stopbits = stopbits
    inst.serial.timeout  = timeout
    inst.serial.parity   = parity
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True

    # ---- FC=1, start=0, qty=8  -> como tus tramas: FF 01 00 00 00 08 CRC ----
    start_addr = 0
    quantity   = 8
    req_payload = struct.pack('>HH', start_addr, quantity)  # big-endian
    try:
        # _perform_command devuelve SOLO el payload de respuesta (sin addr/fc/crc)
        # Para FC=1: b'\x01' + <status_byte>
        resp = inst._perform_command(1, req_payload)
        if not resp or len(resp) < 2:
            raise ValueError(f"Respuesta corta FC1: {resp!r}")
        byte_count = resp[0]
        if byte_count < 1:
            raise ValueError(f"ByteCount inválido en FC1: {byte_count}")
        status_byte = resp[1]  # ← ESTE ES TU 4º byte de la trama total
    except Exception as e:
        util.logging.error(f"[{device_name}] FC1 qty=8 falló: {type(e).__name__}: {e}")
        # Si falla, devolvemos None por cada name
        v_vals = ["None"] * len(names)
        u_vals = [str(regs_by_name.get(n, {}).get('unit', '143')) for n in names]
        return {"d":[{"t": util.get__time_utc(), "g": g_value, "v": v_vals, "u": u_vals}]}

    # Construir v/u según nombres y address de cada relé (bit = address)
    v_vals, u_vals = [], []
    for name in names:
        reg = regs_by_name.get(name)
        if not reg:
            util.logging.error(f"[{device_name}] Relay '{name}' no existe en YAML.")
            v_vals.append("None")
            u_vals.append("143")
            continue
        addr = int(reg.get('address', 0))
        bit_val = (status_byte >> addr) & 0x01
        v_vals.append("1" if bit_val else "0")
        u_vals.append(str(reg.get('unit', '143')))

    return {
        "d": [{
            "t": util.get__time_utc(),
            "g": g_value,         # ← ahora g (no i)
            "v": v_vals,
            "u": u_vals
        }]}
