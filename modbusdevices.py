from logging import config

import minimalmodbus
import serial
import util  # si usas util.get__time_utc() o logging
import threading
import struct
import time

MODBUS_LOCK = threading.RLock()
MODBUS_GAP_S = 0.05
_DIOUSTOU_FAILURES = 0
_DIOUSTOU_RECOVERY_ATTEMPTED = False

'''
Parametros del pto serie modbus
'''
serialPort= "/dev/ttyS0"

#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------

    #Lee temperatura y humedad del sensor THT03R (Modbus RTU) usando la configuración YAML.
    #Espera en config:
    #  - slave_id, baudrate, bytesize, parity, stopbits, timeout
    #  - opcional: port (si no está, usa variable global serialPort)
    #  - registers: lista de dicts con:
    #      { "name": "...", "alias": "...", "address": 0, "unit": 1,
    #        "fc": 3, "decimals": 1, "signed": false }

    #Lee temperatura y humedad del sensor THT03R (Modbus RTU).
    #Compatible con tu YAML reducido (sin fc ni decimals definidos).

def payload_event_modbus(config):
    valores, unidades = [], []
    port = config.get('port', None)
    if port is None:
        port = serialPort
    try:
        with MODBUS_LOCK:
            instrumento = minimalmodbus.Instrument(port, config['slave_id'])
            instrumento.serial.baudrate = config['baudrate']
            instrumento.serial.bytesize = config['bytesize']
            instrumento.serial.stopbits = config['stopbits']
            instrumento.serial.timeout = config['timeout']
            instrumento.serial.inter_byte_timeout = 0.2
            instrumento.mode = minimalmodbus.MODE_RTU
            instrumento.clear_buffers_before_each_transaction = True
            instrumento.close_port_after_each_call = True

            parity_map = {
                'N': serial.PARITY_NONE,
                'E': serial.PARITY_EVEN,
                'O': serial.PARITY_ODD
            }
            instrumento.serial.parity = parity_map.get(config['parity'].upper(), serial.PARITY_NONE)

            device_name = config.get('device_name')
            # ACTIVAR DEBUG MINIMALMODBUS DESDE YAML
            instrumento.debug = bool(config.get('debug', False))

            for reg in config['registers']:
                address = reg['address']
                fc = reg.get('fc')
                decimals = reg.get('decimals')
                signed = bool(reg.get('signed', False))

                try:
                    val = instrumento.read_register(address, decimals, functioncode=fc, signed=signed)
                finally:
                    time.sleep(MODBUS_GAP_S)
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
        util.logging.error(
            f"[{device_name}] Error general al leer el equipo "
            f"(slave={config.get('slave_id')}, port={port}): {type(e).__name__}: {e}"
        )
        return None
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
def _dioustou_response_ok():
    global _DIOUSTOU_FAILURES, _DIOUSTOU_RECOVERY_ATTEMPTED
    _DIOUSTOU_FAILURES = 0
    _DIOUSTOU_RECOVERY_ATTEMPTED = False


def _dioustou_no_response(config, operation):
    global _DIOUSTOU_FAILURES
    _DIOUSTOU_FAILURES += 1
    util.logging.warning(
        f"[{config['device_name']}] Sin respuesta {operation} | "
        f"fallo consecutivo {_DIOUSTOU_FAILURES}"
    )


def _relay_read_packed_locked(inst, config):
    """Lee el bloque FC01 definido en YAML. MODBUS_LOCK debe estar adquirido."""
    span_reg = next(
        (
            reg for reg in config.get('registers', [])
            if reg.get('quantity') is not None and reg.get('fc_read') is not None
        ),
        None
    )
    if span_reg is None:
        raise ValueError("YAML sin registro con quantity y fc_read para lectura empaquetada")

    start_addr = int(span_reg['address'])
    quantity = int(span_reg['quantity'])
    fc_read = int(span_reg['fc_read'])
    if fc_read != 1:
        raise ValueError(f"Lectura empaquetada requiere fc_read=1, recibido {fc_read}")
    if quantity <= 0:
        raise ValueError(f"quantity inválido para FC01: {quantity}")

    req_payload = struct.pack('>HH', start_addr, quantity)
    try:
        try:
            resp = inst._perform_command(fc_read, req_payload)
        except minimalmodbus.NoResponseError:
            _dioustou_no_response(config, "FC01")
            raise
    finally:
        time.sleep(MODBUS_GAP_S)

    if not resp or len(resp) < 2:
        raise ValueError(f"Respuesta corta FC01: {resp!r}")

    byte_count = int(resp[0])
    required_bytes = (quantity + 7) // 8
    if byte_count < required_bytes:
        raise ValueError(
            f"ByteCount insuficiente FC01: {byte_count}, esperado al menos {required_bytes}"
        )
    if len(resp) < 1 + byte_count:
        raise ValueError(
            f"Datos incompletos FC01: recibidos {len(resp) - 1}, anunciados {byte_count}"
        )

    data_bytes = bytes(resp[1:1 + byte_count])
    _dioustou_response_ok()
    return start_addr, quantity, data_bytes


def _relay_state_from_packed(data_bytes, start_addr, quantity, addr):
    """Extrae una coil del bloque packed y valida que pertenezca al rango."""
    offset = int(addr) - int(start_addr)
    if offset < 0 or offset >= int(quantity):
        raise ValueError(
            f"Coil addr={addr} fuera del rango start={start_addr} quantity={quantity}"
        )

    byte_index = offset // 8
    bit_index = offset % 8
    if byte_index >= len(data_bytes):
        raise ValueError(f"Datos FC01 insuficientes para coil addr={addr}")
    return bool((data_bytes[byte_index] >> bit_index) & 0x01)


def _dioustou_recover_locked(config):
    """Ejecuta una única recuperación física y confirma el resultado por FC01."""
    global _DIOUSTOU_RECOVERY_ATTEMPTED
    if _DIOUSTOU_RECOVERY_ATTEMPTED:
        return None

    _DIOUSTOU_RECOVERY_ATTEMPTED = True
    device_name = config['device_name']
    parity_map = {
        'N': serial.PARITY_NONE,
        'E': serial.PARITY_EVEN,
        'O': serial.PARITY_ODD,
    }
    util.logging.warning(f"[{device_name}] Iniciando recuperación controlada")

    try:
        with serial.Serial(
            port=config['port'],
            baudrate=int(config['baudrate']),
            bytesize=int(config['bytesize']),
            parity=parity_map[str(config['parity']).upper()],
            stopbits=int(config['stopbits']),
            timeout=float(config['timeout']),
            inter_byte_timeout=float(config['inter_byte_timeout']),
        ) as recovery_port:
            time.sleep(0.2)
            recovery_port.reset_input_buffer()
            recovery_port.reset_output_buffer()
            recovery_port.write(bytes.fromhex("0D 0A 0D 0A 0D 0A 0D 0A"))
            recovery_port.flush()
            time.sleep(0.5)
            recovery_port.read(64)
            recovery_port.reset_input_buffer()
            recovery_port.reset_output_buffer()

        inst = minimalmodbus.Instrument(config['port'], int(config['slave_id']))
        inst.serial.baudrate = int(config['baudrate'])
        inst.serial.bytesize = int(config['bytesize'])
        inst.serial.stopbits = int(config['stopbits'])
        inst.serial.timeout = float(config['timeout'])
        inst.serial.inter_byte_timeout = float(config['inter_byte_timeout'])
        inst.serial.parity = parity_map[str(config['parity']).upper()]
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = True
        inst.debug = bool(config.get('debug', False))

        packed = _relay_read_packed_locked(inst, config)
        start_addr, quantity, data_bytes = packed
        states = {}
        for reg in config.get('registers', []):
            if str(reg.get('fc_read')) != '1' or reg.get('type') == 'gpio':
                continue
            try:
                states[str(reg['name'])] = _relay_state_from_packed(
                    data_bytes, start_addr, quantity, int(reg['address'])
                )
            except ValueError:
                continue

        util.logging.info(f"[{device_name}] Recuperación OK | FC01 responde")
        util.logging.info(f"[{device_name}] Estados después recuperación: {states}")
        return packed
    except Exception as e:
        util.logging.error(
            f"[{device_name}] Recuperación FALLÓ: {type(e).__name__}: {e}"
        )
        return None


def _dioustou_recover_if_needed_locked(config):
    if _DIOUSTOU_FAILURES < 2 or _DIOUSTOU_RECOVERY_ATTEMPTED:
        return None
    return _dioustou_recover_locked(config)


def relay_set(config, relay_name: str, on: bool = False) -> bool:
    """
    Enciende/Apaga un relé por nombre usando FC=5 (Write Single Coil).
    relay_name: nombre de un registro definido en config['registers']
    Soporta:
      - FC5: Write Single Coil
      - FC15: Write Multiple Coils (para all_off)
    """
    try:
        device_name = config['device_name']
        port = config['port']
        slave = int(config['slave_id'])

        # buscar el registro por nombre
        reg = next((r for r in config.get('registers', []) if r.get('name') == relay_name), None)
        if not reg:
            util.logging.error(f"[{device_name}] Relay '{relay_name}' no existe en YAML.")
            return False

        addr = int(reg['address'])
        fc   = int(reg.get('fc_write'))
        
        with MODBUS_LOCK:
            inst = minimalmodbus.Instrument(port, slave)
            inst.serial.baudrate = int(config['baudrate'])
            inst.serial.bytesize = int(config['bytesize'])
            inst.serial.stopbits = int(config['stopbits'])
            inst.serial.timeout = float(config['timeout'])
            inst.serial.inter_byte_timeout = float(config['inter_byte_timeout'])
            inst.mode = minimalmodbus.MODE_RTU
            inst.clear_buffers_before_each_transaction = True
            inst.close_port_after_each_call = True

            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            inst.serial.parity = parity_map.get(str(config['parity']).upper(), serial.PARITY_NONE)
            inst.debug = bool(config.get('debug', False))

            if fc == 5:
                fc_read_value = reg.get('fc_read')
                if fc_read_value is None or int(fc_read_value) != 1:
                    util.logging.warning(
                        f"[{device_name}] Relay '{relay_name}' sin fc_read=1; "
                        "no se puede confirmar la escritura."
                    )
                    return False
                expected = bool(on)

                def packed_state(packed):
                    start_addr, quantity, data_bytes = packed
                    return _relay_state_from_packed(
                        data_bytes, start_addr, quantity, addr
                    )

                def write_once(stage):
                    try:
                        try:
                            inst.write_bit(addr, 1 if expected else 0, functioncode=fc)
                            _dioustou_response_ok()
                            return True
                        except minimalmodbus.NoResponseError:
                            _dioustou_no_response(config, "FC05")
                            util.logging.warning(
                                f"[{device_name}] FC5 {relay_name} sin ACK | {stage}"
                            )
                            return False
                    finally:
                        time.sleep(MODBUS_GAP_S)

                recovered_packed = None
                try:
                    current = packed_state(_relay_read_packed_locked(inst, config))
                    if current == expected:
                        util.logging.info(
                            f"[{device_name}] {relay_name} ya estaba "
                            f"{'ON' if on else 'OFF'} | CONFIRMADO FC01 PACKED"
                        )
                        return True
                except Exception as e:
                    util.logging.warning(
                        f"[{device_name}] Lectura previa FC01 PACKED falló para "
                        f"'{relay_name}': {type(e).__name__}: {e}"
                    )
                    recovered_packed = _dioustou_recover_if_needed_locked(config)

                if recovered_packed is None:
                    write_once("escritura inicial")
                    try:
                        confirmed = packed_state(_relay_read_packed_locked(inst, config))
                        if confirmed == expected:
                            util.logging.info(
                                f"[{device_name}] {relay_name} CMD={'ON' if on else 'OFF'} "
                                f"REAL={'ON' if confirmed else 'OFF'} CONFIRMADO FC01 PACKED"
                            )
                            return True
                    except Exception as e:
                        util.logging.warning(
                            f"[{device_name}] Read-back FC01 PACKED falló para "
                            f"'{relay_name}': {type(e).__name__}: {e}"
                        )
                    recovered_packed = _dioustou_recover_if_needed_locked(config)

                if recovered_packed is None:
                    util.logging.error(
                        f"[{device_name}] {relay_name} estado NO CONFIRMADO"
                    )
                    return False

                recovered_state = packed_state(recovered_packed)
                if recovered_state == expected:
                    util.logging.info(
                        f"[{device_name}] {relay_name} ya estaba "
                        f"{'ON' if on else 'OFF'} | CONFIRMADO FC01 PACKED"
                    )
                    return True

                write_once("después de recuperación")
                try:
                    confirmed = packed_state(_relay_read_packed_locked(inst, config))
                    if confirmed == expected:
                        util.logging.info(
                            f"[{device_name}] {relay_name} CMD={'ON' if on else 'OFF'} "
                            f"REAL={'ON' if confirmed else 'OFF'} CONFIRMADO FC01 PACKED"
                        )
                        return True
                except Exception as e:
                    util.logging.warning(
                        f"[{device_name}] Confirmación posterior a recuperación falló para "
                        f"'{relay_name}': {type(e).__name__}: {e}"
                    )

                util.logging.error(f"[{device_name}] {relay_name} estado NO CONFIRMADO")
                return False

            elif fc == 15:
                qty = int(reg['quantity'])
                data_hex = reg['data_hex']
                data = bytes.fromhex(data_hex)
                payload = bytes([
                    (addr >> 8) & 0xFF, addr & 0xFF,
                    (qty >> 8) & 0xFF, qty & 0xFF,
                    len(data)
                ]) + data
                try:
                    try:
                        inst._perform_command(fc, payload)
                        _dioustou_response_ok()
                    except minimalmodbus.NoResponseError:
                        _dioustou_no_response(config, "FC15")
                        raise
                finally:
                    time.sleep(MODBUS_GAP_S)
                util.logging.info(f"[{device_name}] FC15 {relay_name} (addr={addr} qty={qty}) enviado OK")
                return True

            else:
                util.logging.warning(f"[{device_name}] Función no soportada fc_write={fc} para {relay_name}")
                return False

    except Exception as e:
        util.logging.error(
            f"[{config.get('device_name','Relay')}] Error al escribir relay '{relay_name}': "
            f"{type(e).__name__}: {e}"
        )
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
        device_name = config['device_name']
        port = config['port']
        slave = int(config['slave_id'])

        with MODBUS_LOCK:
            inst = minimalmodbus.Instrument(port, slave)
            inst.serial.baudrate = int(config['baudrate'])
            inst.serial.bytesize = int(config['bytesize'])
            inst.serial.stopbits = int(config['stopbits'])
            inst.serial.timeout = float(config['timeout'])
            inst.serial.inter_byte_timeout = float(config['inter_byte_timeout'])
            inst.mode = minimalmodbus.MODE_RTU
            inst.clear_buffers_before_each_transaction = True
            inst.close_port_after_each_call = True

            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            inst.serial.parity = parity_map.get(str(config['parity']).upper(), serial.PARITY_NONE)

            relay_regs = [
                reg for reg in config.get('registers', [])
                if reg.get('type') != 'gpio'
            ]
            try:
                start_addr, quantity, data_bytes = _relay_read_packed_locked(inst, config)
            except Exception as e:
                util.logging.warning(
                    f"[{device_name}] Lectura FC01 PACKED falló: {type(e).__name__}: {e}"
                )
                recovered = _dioustou_recover_if_needed_locked(config)
                if recovered is None:
                    return {reg.get('name'): None for reg in relay_regs}
                start_addr, quantity, data_bytes = recovered

            for reg in relay_regs:
                if reg.get('type') == 'gpio':
                    continue
                name = reg.get('name')
                addr = int(reg['address'])
                fc_read_value = reg.get('fc_read')
                if fc_read_value is None or int(fc_read_value) != 1:
                    util.logging.warning(
                        f"[{device_name}] Relay '{name}' sin fc_read=1; no se puede leer estado."
                    )
                    estados[name] = None
                    continue
                try:
                    estados[name] = _relay_state_from_packed(
                        data_bytes, start_addr, quantity, addr
                    )
                except Exception as e:
                    util.logging.warning(
                        f"[{device_name}] No se pudo extraer '{name}' (addr={addr}) "
                        f"de FC01 PACKED: {type(e).__name__}: {e}"
                    )
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
    device_name = config['device_name']
    i_value = int(config.get('i', config['id_device']))

    port     = config['port']
    slave    = int(config['slave_id'])
    baud     = int(config['baudrate'])
    bytesize = int(config['bytesize'])
    stopbits = int(config['stopbits'])
    timeout  = float(config['timeout'])
    parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
    parity  = parity_map[str(config['parity']).upper()]

    # Instancia Modbus
    with MODBUS_LOCK:
        inst = minimalmodbus.Instrument(port, slave)
        inst.serial.baudrate = baud
        inst.serial.bytesize = bytesize
        inst.serial.stopbits = stopbits
        inst.serial.timeout  = timeout
        inst.serial.inter_byte_timeout = float(config['inter_byte_timeout'])
        inst.serial.parity   = parity
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = True

        try:
            start_addr, quantity, data_bytes = _relay_read_packed_locked(inst, config)
        except Exception as e:
            util.logging.error(
                f"[{device_name}] FC01 PACKED falló: {type(e).__name__}: {e}"
            )
            recovered = _dioustou_recover_if_needed_locked(config)
            if recovered is None:
                start_addr, quantity, data_bytes = None, None, None
            else:
                start_addr, quantity, data_bytes = recovered

        # Índice rápido por nombre
        regs_by_name = {str(r.get('name')): r for r in config.get('registers', [])}

        v_vals, u_vals = [], []
        for name in names:
            reg = regs_by_name.get(name)
            if not reg:
                util.logging.error(f"[{device_name}] Relay '{name}' no existe en YAML.")
                v_vals.append("None")
                u_vals.append("None")
                continue

            if str(reg.get('fc_read', '')) != '1':
                util.logging.warning(f"[{device_name}] Relay '{name}' sin fc_read=1; no se puede leer estado.")
                v_vals.append("None")
                u_vals.append(str(reg['unit']))
                continue

            addr = int(reg['address'])
            if data_bytes is None:
                v_vals.append("None")
                u_vals.append(str(reg['unit']))
                continue
            try:
                bit = _relay_state_from_packed(data_bytes, start_addr, quantity, addr)
                v_vals.append("1" if bit else "0")
            except Exception as e:
                util.logging.error(
                    f"[{device_name}] Extraer '{name}' addr={addr} de FC01 PACKED "
                    f"falló: {type(e).__name__}: {e}"
                )
                v_vals.append("None")

            u_vals.append(str(reg['unit']))

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
    Lee en una sola FC01 el rango definido por YAML y arma UN payload:
      g = config['id_device'] (o 'i' si no existe)
      v = ["1"/"0"] por cada 'name' (orden dado)
      u = unidad por cada relé, tomada del YAML
    Cada estado se extrae en memoria según su address definido en YAML.
    """
    device_name = config['device_name']
    g_value = int(config['id_device'] if 'id_device' in config else config['i'])

    port     = config['port']
    slave    = int(config['slave_id'])
    baud     = int(config['baudrate'])
    bytesize = int(config['bytesize'])
    stopbits = int(config['stopbits'])
    timeout  = float(config['timeout'])
    parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
    parity  = parity_map[str(config['parity']).upper()]

    # índice por nombre
    regs_by_name = {str(r.get('name')): r for r in (config.get('registers') or [])}

    invalid_names = set()
    for name in names:
        reg = regs_by_name.get(name)
        if not reg:
            util.logging.warning(f"[{device_name}] Relay '{name}' no existe en YAML.")
            invalid_names.add(name)
            continue
        if str(reg.get('fc_read')) != '1':
            util.logging.warning(f"[{device_name}] Relay '{name}' sin fc_read=1; se omite de FC01.")
            invalid_names.add(name)
            continue

    start_addr, quantity, data_bytes = None, None, None
    with MODBUS_LOCK:
        inst = minimalmodbus.Instrument(port, slave)
        inst.serial.baudrate = baud
        inst.serial.bytesize = bytesize
        inst.serial.stopbits = stopbits
        inst.serial.timeout  = timeout
        inst.serial.inter_byte_timeout = float(config['inter_byte_timeout'])
        inst.serial.parity   = parity
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = True

        try:
            start_addr, quantity, data_bytes = _relay_read_packed_locked(inst, config)
        except minimalmodbus.NoResponseError as first_error:
            util.logging.error(
                f"[{device_name}] FC01 PACKED falló: "
                f"{type(first_error).__name__}: {first_error}"
            )
            recovered = _dioustou_recover_if_needed_locked(config)

            # Un único segundo FC01 permite confirmar el fallo consecutivo sin
            # crear loops ni escribir coils durante la consulta de AWS.
            if recovered is None and not _DIOUSTOU_RECOVERY_ATTEMPTED:
                try:
                    start_addr, quantity, data_bytes = _relay_read_packed_locked(inst, config)
                except minimalmodbus.NoResponseError as second_error:
                    util.logging.error(
                        f"[{device_name}] Segundo FC01 PACKED falló: "
                        f"{type(second_error).__name__}: {second_error}"
                    )
                    recovered = _dioustou_recover_if_needed_locked(config)
                except Exception as second_error:
                    util.logging.error(
                        f"[{device_name}] Segundo FC01 PACKED inválido: "
                        f"{type(second_error).__name__}: {second_error}"
                    )

            if recovered is not None:
                start_addr, quantity, data_bytes = recovered
                util.logging.info(
                    f"[{device_name}] FC01 PACKED recuperado para payload AWS"
                )
        except Exception as e:
            util.logging.error(
                f"[{device_name}] FC01 PACKED inválido: {type(e).__name__}: {e}"
            )

    # Construir v/u según nombres y address de cada relé (bit = address)
    v_vals, u_vals = [], []
    for name in names:
        reg = regs_by_name.get(name)
        if name in invalid_names or not reg:
            v_vals.append("None")
            u_vals.append(str(reg['unit']) if reg else "None")
            continue
        addr = int(reg['address'])
        if data_bytes is None:
            v_vals.append("None")
            u_vals.append(str(reg['unit']))
            continue
        try:
            bit_val = _relay_state_from_packed(data_bytes, start_addr, quantity, addr)
            v_vals.append("1" if bit_val else "0")
        except Exception as e:
            util.logging.warning(
                f"[{device_name}] Extraer '{name}' addr={addr} de FC01 PACKED "
                f"falló: {type(e).__name__}: {e}"
            )
            v_vals.append("None")
        u_vals.append(str(reg['unit']))

    util.logging.info(
        f"[AWS][RELAYS] g={g_value} v={v_vals} u={u_vals}"
    )

    return {
        "d": [{
            "t": util.get__time_utc(),
            "g": g_value,         # ← ahora g (no i)
            "v": v_vals,
            "u": u_vals
        }]}

def payload_event_modbus_promedio(config, muestras=10, delay_s=1, decimales=1):

    acumulados = None
    cantidad_ok = 0
    ultimo_payload = None

    for i in range(muestras):

        try:

            payload = payload_event_modbus(config)

            if not payload:
                time.sleep(delay_s)
                continue

            ultimo_payload = payload

            valores = payload.get("d", [{}])[0].get("v", [])

            valores_float = []
            valido = True

            for v in valores:

                if v in [None, "None", ""]:
                    valido = False
                    break

                valores_float.append(float(v))

            if not valido:
                time.sleep(delay_s)
                continue

            if acumulados is None:
                acumulados = [0.0] * len(valores_float)

            for idx, val in enumerate(valores_float):
                acumulados[idx] += val

            cantidad_ok += 1

        except Exception as e:

            util.logging.error(
                f"[PROMEDIO] {config.get('device_name')} "
                f"error muestra {i+1}: {e}"
            )

        time.sleep(delay_s)

    if cantidad_ok == 0 or acumulados is None:

        util.logging.warning(
            f"[PROMEDIO] {config.get('device_name')} "
            f"sin muestras válidas"
        )

        return ultimo_payload

    promedios = [
        round(v / cantidad_ok, decimales)
        for v in acumulados
    ]

    ultimo_payload["d"][0]["v"] = [
        str(v)
        for v in promedios
    ]

    ultimo_payload["d"][0]["t"] = util.get__time_utc()

    util.logging.info(
        f"[PROMEDIO] {config.get('device_name')} "
        f"resultado final {cantidad_ok}/{muestras}: {promedios}"
    )

    return ultimo_payload
