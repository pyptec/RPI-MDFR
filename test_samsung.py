#!/usr/bin/env python3

import time
import serial
import util
import os

from dotenv import load_dotenv

load_dotenv("/home/pi/.scr/.scr/RPI-MDFR/.env")


# =========================================================
# CONFIGURACIÓN
# =========================================================

PORT = "/dev/ttyUSB5"
BAUDRATE = 9600
PARITY = 'E'
BYTESIZE = 8
STOPBITS = 1
TIMEOUT = 2


# =========================================================
# FUNCIÓN RAW MODBUS
# =========================================================

def enviar_cmd_raw(hex_cmd, descripcion="CMD HVAC"):

    print("\n===================================")
    print(f"{descripcion}")
    print("===================================")

    print(f"Puerto    : {PORT}")
    print(f"Baudrate  : {BAUDRATE}")
    print(f"Bytesize  : {BYTESIZE}")
    print(f"Parity    : EVEN")
    print(f"Stopbits  : {STOPBITS}")
    print(f"Timeout   : {TIMEOUT}")

    tx = bytes.fromhex(hex_cmd)

    try:

        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=BYTESIZE,
            parity=PARITY,
            stopbits=STOPBITS,
            timeout=TIMEOUT
        )

        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("\nTX:", tx.hex(" ").upper())

        ser.write(tx)

        # Samsung responde lento
        time.sleep(1)

        rx = ser.read(100)

        if rx:

            print("RX:", rx.hex(" ").upper())

            # Communication status decode
            if hex_cmd == "01 03 00 00 00 01 84 0A":

                if len(rx) >= 5:

                    status = int.from_bytes(rx[3:5], byteorder='big')

                    print(f"\nCommunication Status = {status}")

                    if status == 7:
                        print("HVAC READY")

                    elif status == 0:
                        print("HVAC NOT READY")

                    else:
                        print("HVAC estado intermedio")

        else:

            print("RX: TIMEOUT / SIN RESPUESTA")

        ser.close()

        return rx

    except Exception as e:

        print(
            f"\nERROR enviando comando: "
            f"{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# COMANDOS HVAC
# =========================================================

def test_status():

    enviar_cmd_raw(
        "01 03 00 00 00 01 84 0A",
        "LEER COMMUNICATION STATUS"
    )


def test_on():

    enviar_cmd_raw(
        "01 06 00 02 00 01 E9 CA",
        "HVAC ON"
    )


def test_off():

    enviar_cmd_raw(
        "01 06 00 02 00 00 28 0A",
        "HVAC OFF"
    )


def test_cool():

    enviar_cmd_raw(
        "01 06 00 03 00 01 B8 0A",
        "MODO COOL"
    )


def test_setpoint_20():

    enviar_cmd_raw(
        "01 06 00 08 00 C8 09 9C",
        "SETPOINT 20.0C"
    )


def test_setpoint_18():

    enviar_cmd_raw(
        "01 06 00 08 00 B4 08 11",
        "SETPOINT 18.0C"
    )


def test_room_temp():

    enviar_cmd_raw(
        "01 03 00 09 00 01 54 08",
        "LEER ROOM TEMPERATURE"
    )


def test_error_code():

    enviar_cmd_raw(
        "01 03 00 0A 00 01 A4 08",
        "LEER ERROR CODE"
    )

def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF

    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    return crc.to_bytes(2, byteorder="little")


def leer_registro_raw(reg):
    slave = 1

    frame = bytes([
        slave,
        0x03,
        (reg >> 8) & 0xFF,
        reg & 0xFF,
        0x00,
        0x01
    ])

    frame += crc16_modbus(frame)

    return enviar_cmd_raw(
        frame.hex(" "),
        f"LEER REGISTRO {reg}"
    )


def scan_read_only():
    print("\n=== SCAN SOLO LECTURA HVAC ===")
    print("No escribe nada en el equipo. Solo usa FC03.")

    for reg in range(0, 21):
        leer_registro_raw(reg)
        time.sleep(0.5)
# =========================================================
# MENÚ
# =========================================================

def menu():

    while True:

        print("""
=========================================
 TEST SAMSUNG HVAC RAW MODBUS
=========================================

1. Leer Communication Status
2. HVAC ON
3. HVAC OFF
4. Modo COOL
5. Setpoint 20C
6. Setpoint 18C
7. Leer temperatura ambiente
8. Leer Error Code
9. Secuencia completa
10. Scan solo lectura registros 0 a 20
0. Salir

=========================================
""")

        op = input("Seleccione opción: ").strip()

        if op == "1":

            test_status()

        elif op == "2":

            test_on()

        elif op == "3":

            test_off()

        elif op == "4":

            test_cool()

        elif op == "5":

            test_setpoint_20()

        elif op == "6":

            test_setpoint_18()

        elif op == "7":

            test_room_temp()

        elif op == "8":

            test_error_code()

        elif op == "9":

            print("\n=== SECUENCIA HVAC ===")

            test_status()
            time.sleep(1)

            test_cool()
            time.sleep(1)

            test_on()
            time.sleep(1)

            test_setpoint_20()
        
        elif op == "10":
            scan_read_only()

        elif op == "0":

            print("Saliendo...")
            break

        else:

            print("Opción inválida.")

        input("\nENTER para continuar...")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    menu()