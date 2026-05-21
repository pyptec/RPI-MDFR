#!/usr/bin/env python3
import os
import time
import serial
import minimalmodbus
import util
from dotenv import load_dotenv

load_dotenv("/home/pi/.scr/.scr/RPI-MDFR/.env")


def _cfg():
    return util.cargar_configuracion(
        os.getenv("CFG_SAMSUNG"),
        os.getenv("CFG_SAMSUNG_SECTION")
    )


def _inst(cfg):
    port = cfg.get("port", "/dev/ttyUSB0")
    slave = int(cfg.get("slave_id", 1))

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = int(cfg.get("baudrate", 9600))
    ser.bytesize = int(cfg.get("bytesize", 8))
    ser.stopbits = int(cfg.get("stopbits", 1))
    ser.timeout = float(cfg.get("timeout", 1))
    ser.write_timeout = 2.0
    ser.inter_byte_timeout = 0.2
    ser.parity = serial.PARITY_EVEN

    ser.xonxoff = False
    ser.rtscts = False
    ser.dsrdtr = False
    ser.dtr = False
    ser.rts = False

    ser.open()

    inst = minimalmodbus.Instrument(port, slave)
    inst.serial = ser
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = False

    return inst


def activar_debug_tx_rx(inst):
    original_write = inst.serial.write
    original_read = inst.serial.read

    def write_debug(data):
        print("TX:", data.hex(" ").upper())
        return original_write(data)

    def read_debug(size=1):
        data = original_read(size)
        if data:
            print("RX:", data.hex(" ").upper())
        else:
            print("RX: TIMEOUT / SIN RESPUESTA")
        return data

    inst.serial.write = write_debug
    inst.serial.read = read_debug


def imprimir_config(cfg):
    print("\n=== CONFIGURACIÓN SAMSUNG HVAC ===")
    print(f"Puerto    : {cfg.get('port', '/dev/ttyUSB0')}")
    print(f"Slave ID  : {cfg.get('slave_id', 1)}")
    print(f"Baudrate  : {cfg.get('baudrate', 9600)}")
    print(f"Bytesize  : {cfg.get('bytesize', 8)}")
    print(f"Parity    : {cfg.get('parity', 'E')}")
    print(f"Stopbits  : {cfg.get('stopbits', 1)}")
    print(f"Timeout   : {cfg.get('timeout', 1)}")
    print("=================================\n")


def leer_registro(address, decimals=0, signed=False, descripcion=""):
    cfg = _cfg()
    inst = _inst(cfg)
    activar_debug_tx_rx(inst)

    print(f"\n--- LEER {descripcion} ---")
    print(f"Registro: {address}")

    try:
        value = inst.read_register(
            int(address),
            int(decimals),
            functioncode=3,
            signed=bool(signed)
        )

        print(f"Valor leído: {value}")
        return value

    except Exception as e:
        print(f"ERROR leyendo {descripcion}: {type(e).__name__}: {e}")
        return None


def escribir_registro(address, value, descripcion=""):
    cfg = _cfg()
    inst = _inst(cfg)
    activar_debug_tx_rx(inst)

    print(f"\n--- ESCRIBIR {descripcion} ---")
    print(f"Registro: {address}")
    print(f"Valor: {value}")

    try:
        inst.write_register(
            int(address),
            int(value),
            functioncode=6
        )

        print("Escritura enviada correctamente.")
        return True

    except Exception as e:
        print(f"ERROR escribiendo {descripcion}: {type(e).__name__}: {e}")
        return False


def leer_status():
    value = leer_registro(
        address=0,
        decimals=0,
        signed=False,
        descripcion="Communication Status"
    )

    print(f"\nCommunication Status = {value}")

    if value == 7:
        print("HVAC READY")
    elif value == 0:
        print("HVAC NOT READY")
    elif value is None:
        print("Sin respuesta válida")
    else:
        print("HVAC estado intermedio")

    return value


def leer_onoff():
    value = leer_registro(2, 0, False, "OnOff")

    if value == 1:
        print("Estado OnOff: ON")
    elif value == 0:
        print("Estado OnOff: OFF")

    return value


def encender_hvac():
    return escribir_registro(2, 1, "HVAC ON")


def apagar_hvac():
    return escribir_registro(2, 0, "HVAC OFF")


def leer_modo():
    value = leer_registro(3, 0, False, "Operation Mode")

    modos = {
        0: "Auto",
        1: "Cool",
        2: "Dry",
        3: "Fan",
        4: "Heat"
    }

    print(f"Modo: {modos.get(value, 'Desconocido')}")
    return value


def modo_cool():
    return escribir_registro(3, 1, "Modo COOL")


def leer_fan():
    value = leer_registro(4, 0, False, "Fan Speed")

    fans = {
        0: "Auto",
        1: "Low",
        2: "Medium",
        3: "High"
    }

    print(f"Fan: {fans.get(value, 'Desconocido')}")
    return value


def set_fan():
    print("\n0=Auto | 1=Low | 2=Medium | 3=High")
    fan = input("Seleccione fan: ").strip()

    if fan not in ["0", "1", "2", "3"]:
        print("Fan inválido.")
        return False

    return escribir_registro(4, int(fan), f"Fan Speed {fan}")


def leer_setpoint():
    value = leer_registro(8, 0, True, "Set Temperature")

    if value is not None:
        print(f"Setpoint: {value / 10:.1f} °C")

    return value


def set_setpoint():
    temp = input("Ingrese setpoint °C. Ejemplo 20.0: ").strip()

    try:
        temp_c = float(temp)
    except ValueError:
        print("Temperatura inválida.")
        return False

    value = int(round(temp_c * 10))

    print(f"{temp_c:.1f} °C -> valor Modbus {value}")

    return escribir_registro(8, value, f"Setpoint {temp_c:.1f} °C")


def leer_room_temp():
    value = leer_registro(9, 0, True, "Room Temperature")

    if value is not None:
        print(f"Room Temperature: {value / 10:.1f} °C")

    return value


def leer_error_code():
    value = leer_registro(10, 0, False, "Error Code")
    print(f"Error Code: {value}")
    return value


def leer_todo():
    print("\n=== LECTURA GENERAL HVAC ===")
    leer_status()
    time.sleep(0.2)
    leer_onoff()
    time.sleep(0.2)
    leer_modo()
    time.sleep(0.2)
    leer_fan()
    time.sleep(0.2)
    leer_setpoint()
    time.sleep(0.2)
    leer_room_temp()
    time.sleep(0.2)
    leer_error_code()


def secuencia_prueba():
    print("\n=== SECUENCIA DE PRUEBA ===")
    print("Esta secuencia intentará:")
    print("1. Leer status")
    print("2. Poner modo COOL")
    print("3. Encender HVAC")
    print("4. Setpoint 20.0 °C")

    confirmar = input("¿Continuar? (s/n): ").strip().lower()

    if confirmar != "s":
        return

    status = leer_status()

    if status != 7:
        print("\nADVERTENCIA: HVAC no está READY.")
        print("No se recomienda enviar comandos de control.")
        continuar = input("¿Enviar de todas formas? (s/n): ").strip().lower()

        if continuar != "s":
            return

    modo_cool()
    time.sleep(0.5)
    encender_hvac()
    time.sleep(0.5)
    escribir_registro(8, 200, "Setpoint 20.0 °C")


def menu():
    cfg = _cfg()

    while True:
        imprimir_config(cfg)

        print("""
===============================
 TEST SAMSUNG HVAC MIM-B19N
===============================

1. Leer Communication Status
2. Leer OnOff
3. Encender HVAC
4. Apagar HVAC
5. Leer modo
6. Colocar modo COOL
7. Leer fan speed
8. Cambiar fan speed
9. Leer setpoint
10. Cambiar setpoint
11. Leer room temperature
12. Leer error code
13. Leer todo
14. Secuencia prueba COOL + ON + 20°C
0. Salir
""")

        op = input("Seleccione opción: ").strip()

        if op == "1":
            leer_status()
        elif op == "2":
            leer_onoff()
        elif op == "3":
            encender_hvac()
        elif op == "4":
            apagar_hvac()
        elif op == "5":
            leer_modo()
        elif op == "6":
            modo_cool()
        elif op == "7":
            leer_fan()
        elif op == "8":
            set_fan()
        elif op == "9":
            leer_setpoint()
        elif op == "10":
            set_setpoint()
        elif op == "11":
            leer_room_temp()
        elif op == "12":
            leer_error_code()
        elif op == "13":
            leer_todo()
        elif op == "14":
            secuencia_prueba()
        elif op == "0":
            print("Saliendo.")
            break
        else:
            print("Opción no válida.")

        input("\nPresione ENTER para continuar...")


if __name__ == "__main__":
    menu()