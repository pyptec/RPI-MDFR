#!/usr/bin/env python3

import time
import json
import yaml
import minimalmodbus
import serial
from pathlib import Path

# =========================================================
# ARCHIVOS
# =========================================================

YAML_FILE = "/home/pi/.scr/.scr/RPI-MDFR/device/samsung_mim_b19n.yml"
CAL_FILE = "/home/pi/.scr/.scr/RPI-MDFR/calibracion_pt21a01.json"

# =========================================================
# REGISTROS MODBUS SAMSUNG
# =========================================================

IU = 0
BASE = 50 * IU

REG_COMM = BASE + 0
REG_ONOFF = BASE + 2
REG_MODE = BASE + 3
REG_FAN = BASE + 4
REG_SETPOINT = BASE + 8
REG_ROOM_TEMP = BASE + 9
REG_ERROR = BASE + 10

# =========================================================
# ESTADO SIMULADO HVAC
# =========================================================

SIM_STATE = {
    "comm": 7,
    "onoff": 0,
    "mode": 1,
    "fan": 0,
    "setpoint": 20.0,
    "room": 19.5,
    "error": 0
}

# =========================================================
# YAML
# =========================================================

def cargar_yaml():
    with open(YAML_FILE, "r") as f:
        data = yaml.safe_load(f)

    return data["medidores"]["samsung_mim_b19n"]

# =========================================================
# MODBUS
# =========================================================

def crear_inst(cfg):

    slave = int(cfg.get("slave", cfg.get("slave_id", 1)))

    inst = minimalmodbus.Instrument(
        cfg["port"],
        slave
    )

    inst.serial.baudrate = int(cfg["baudrate"])
    inst.serial.bytesize = int(cfg["bytesize"])
    inst.serial.stopbits = int(cfg["stopbits"])
    inst.serial.timeout = float(cfg.get("timeout", 1))
    inst.serial.inter_byte_timeout = 0.2

    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD
    }

    inst.serial.parity = parity_map.get(
        str(cfg["parity"]).upper(),
        serial.PARITY_NONE
    )

    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = bool(cfg.get("debug", False))

    return inst

# =========================================================
# LECTURA / ESCRITURA
# =========================================================

def leer_reg(inst, address, signed=False, decimals=0):

    return inst.read_register(
        address,
        decimals,
        functioncode=3,
        signed=signed
    )

def escribir_reg(inst, address, value):

    inst.write_register(
        address,
        int(value),
        functioncode=6
    )

# =========================================================
# HVAC
# =========================================================

def leer_estado(inst, simular=False):

    if simular:

        print("\n--- ESTADO SAMSUNG HVAC SIMULADO ---")

        print(f"Communication status : {SIM_STATE['comm']}")
        print(f"On/Off               : {SIM_STATE['onoff']}")

        print(f"Mode                 : {SIM_STATE['mode']}")
        print(f"Fan                  : {SIM_STATE['fan']}")

        print(f"Setpoint             : {SIM_STATE['setpoint']:.1f} °C")
        print(f"Room temp Samsung    : {SIM_STATE['room']:.1f} °C")

        print(f"Error code           : {SIM_STATE['error']}")

        print("------------------------------------\n")

        return

    comm = leer_reg(inst, REG_COMM)

    onoff = leer_reg(inst, REG_ONOFF)

    mode = leer_reg(inst, REG_MODE)

    fan = leer_reg(inst, REG_FAN)

    setpoint = leer_reg(inst, REG_SETPOINT) / 10

    room = leer_reg(
        inst,
        REG_ROOM_TEMP,
        signed=True
    ) / 10

    error = leer_reg(inst, REG_ERROR)

    print("\n--- ESTADO SAMSUNG HVAC ---")

    print(f"Communication status : {comm}")

    print(f"On/Off               : {onoff}")

    print(f"Mode                 : {mode}")

    print(f"Fan                  : {fan}")

    print(f"Setpoint             : {setpoint:.1f} °C")

    print(f"Room temp Samsung    : {room:.1f} °C")

    print(f"Error code           : {error}")

    print("----------------------------\n")

def set_onoff(inst, estado, simular=False):

    if simular:

        SIM_STATE["onoff"] = 1 if estado else 0

        print("[SIM] HVAC ON" if estado else "[SIM] HVAC OFF")

        return

    escribir_reg(
        inst,
        REG_ONOFF,
        1 if estado else 0
    )

    print("HVAC ON" if estado else "HVAC OFF")

def set_mode_cool(inst, simular=False):

    if simular:

        SIM_STATE["mode"] = 1

        print("[SIM] Modo COOL enviado")

        return

    escribir_reg(inst, REG_MODE, 1)

    print("Modo COOL enviado")

def set_fan(inst, fan, simular=False):

    if fan not in [0, 1, 2, 3]:

        print("Fan inválido")

        return

    if simular:

        SIM_STATE["fan"] = fan

        print(f"[SIM] Fan enviado: {fan}")

        return

    escribir_reg(inst, REG_FAN, fan)

    print(f"Fan enviado: {fan}")

def set_temp(inst, temp_c, simular=False):

    valor = int(round(temp_c * 10))

    if simular:

        SIM_STATE["setpoint"] = temp_c

        print(
            f"[SIM] Setpoint enviado: "
            f"{temp_c:.1f} °C "
            f"-> valor Modbus {valor}"
        )

        return

    escribir_reg(inst, REG_SETPOINT, valor)

    print(
        f"Setpoint enviado: "
        f"{temp_c:.1f} °C "
        f"-> valor Modbus {valor}"
    )

# =========================================================
# CALIBRACIÓN PT21A01
# =========================================================

def cargar_calibracion():

    if not Path(CAL_FILE).exists():

        return {
            "m": 1.0,
            "b": 0.0
        }

    with open(CAL_FILE, "r") as f:

        return json.load(f)

def aplicar_calibracion(temp_pt21):

    cal = cargar_calibracion()

    m = float(cal.get("m", 1.0))

    b = float(cal.get("b", 0.0))

    return round((m * temp_pt21) + b, 2)

# =========================================================
# CONTROL MDFR
# =========================================================

def calcular_setpoint_por_banano(temp_banano):

    """
    RTD 15 °C -> HVAC 16 °C
    RTD 16 °C -> HVAC 17 °C
    RTD 17 °C -> HVAC 18 °C
    RTD 18 °C -> HVAC 19 °C
    RTD >=19 °C -> HVAC 20 °C
    """

    if temp_banano < 15.5:

        return 16.0

    elif temp_banano < 16.5:

        return 17.0

    elif temp_banano < 17.5:

        return 18.0

    elif temp_banano < 18.5:

        return 19.0

    else:

        return 20.0

# =========================================================
# PRUEBAS
# =========================================================

def prueba_control_calibrado(inst, simular):

    dato = input(
        "Ingrese temperatura PT21A01: "
    ).strip()

    temp_pt21 = float(dato)

    temp_cal = aplicar_calibracion(temp_pt21)

    setpoint = calcular_setpoint_por_banano(
        temp_cal
    )

    print("\n--- CONTROL MDFR CALIBRADO ---")

    print(f"PT21A01 leído         : {temp_pt21:.2f} °C")

    print(f"Temperatura calibrada : {temp_cal:.2f} °C")

    print(f"Setpoint HVAC         : {setpoint:.1f} °C")

    confirmar = input(
        "¿Enviar setpoint? (s/n): "
    ).strip().lower()

    if confirmar == "s":

        set_mode_cool(inst, simular)

        time.sleep(0.2)

        set_onoff(inst, True, simular)

        time.sleep(0.2)

        set_temp(inst, setpoint, simular)

def prueba_escalonada(inst, simular):

    dato = input(
        "Ingrese temperatura RTD/PT21A01: "
    ).strip()

    temp_rtd = float(dato)

    setpoint = calcular_setpoint_por_banano(
        temp_rtd
    )

    print("\n--- TEST ESCALONADO RTD → HVAC ---")

    print(f"Temperatura RTD : {temp_rtd:.1f} °C")

    print(f"Setpoint HVAC   : {setpoint:.1f} °C")

    confirmar = input(
        "¿Enviar este setpoint? (s/n): "
    ).strip().lower()

    if confirmar == "s":

        set_mode_cool(inst, simular)

        time.sleep(0.2)

        set_onoff(inst, True, simular)

        time.sleep(0.2)

        set_temp(inst, setpoint, simular)

        print("Comando enviado.")

def prueba_secuencia(inst, simular):

    print("\n--- PRUEBA SECUENCIA HVAC ---")

    print(
        "Se enviarán: "
        "16,17,18,19,20 °C"
    )

    confirmar = input(
        "¿Continuar? (s/n): "
    ).strip().lower()

    if confirmar != "s":

        return

    set_mode_cool(inst, simular)

    time.sleep(0.5)

    set_onoff(inst, True, simular)

    time.sleep(0.5)

    for sp in [16, 17, 18, 19, 20]:

        set_temp(inst, sp, simular)

        time.sleep(2)

        leer_estado(inst, simular)

    print(
        "Secuencia finalizada."
    )

# =========================================================
# MENU
# =========================================================

def menu():

    cfg = cargar_yaml()

    simular = bool(cfg.get("simular", False))

    inst = None if simular else crear_inst(cfg)

    if simular:

        print(
            "\n"
            "=================================\n"
            " MODO SIMULACIÓN HVAC ACTIVADO\n"
            "=================================\n"
        )

    while True:

        print("""
====================================
 TEST SAMSUNG MIM-B19N - MDFR
====================================

1. Leer estado HVAC
2. Encender HVAC
3. Apagar HVAC
4. Colocar modo COOL
5. Cambiar velocidad ventilador
6. Cambiar setpoint manual
7. Prueba control calibrado PT21A01
8. Ver calibración PT21A01
9. Test escalonado RTD → HVAC
10. Secuencia automática 16→20 °C
0. Salir
""")

        op = input(
            "Seleccione opción: "
        ).strip()

        try:

            if op == "1":

                leer_estado(inst, simular)

            elif op == "2":

                set_onoff(
                    inst,
                    True,
                    simular
                )

            elif op == "3":

                set_onoff(
                    inst,
                    False,
                    simular
                )

            elif op == "4":

                set_mode_cool(
                    inst,
                    simular
                )

            elif op == "5":

                print(
                    "0=Auto "
                    "1=Low "
                    "2=Medium "
                    "3=High"
                )

                fan = int(
                    input("Fan: ").strip()
                )

                set_fan(
                    inst,
                    fan,
                    simular
                )

            elif op == "6":

                temp = float(
                    input(
                        "Setpoint °C: "
                    ).strip()
                )

                set_temp(
                    inst,
                    temp,
                    simular
                )

            elif op == "7":

                prueba_control_calibrado(
                    inst,
                    simular
                )

            elif op == "8":

                print(
                    json.dumps(
                        cargar_calibracion(),
                        indent=4
                    )
                )

            elif op == "9":

                prueba_escalonada(
                    inst,
                    simular
                )

            elif op == "10":

                prueba_secuencia(
                    inst,
                    simular
                )

            elif op == "0":

                break

            else:

                print(
                    "Opción no válida"
                )

        except Exception as e:

            print(
                f"ERROR: "
                f"{type(e).__name__}: {e}"
            )

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    menu()