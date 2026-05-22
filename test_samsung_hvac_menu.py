#!/usr/bin/env python3
import time
import serial

PORT = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0OI4DA-if00-port0"
BAUDRATE = 9600
TIMEOUT = 2
SLAVE = 1

REG_STATUS = 50
REG_UNIT_TYPE = 51
REG_ONOFF = 52
REG_MODE = 53
REG_FAN = 54
REG_SETPOINT = 58      # Setpoint activo confirmado
REG_ROOM_TEMP = 59     # Temperatura ambiente real confirmada
REG_ERROR = 63


def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, byteorder="little")


def enviar_frame(frame):
    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="E",
        stopbits=1,
        timeout=TIMEOUT
    ) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("TX:", frame.hex(" ").upper())
        ser.write(frame)
        time.sleep(1)

        rx = ser.read(100)
        print("RX:", rx.hex(" ").upper() if rx else "TIMEOUT / SIN RESPUESTA")
        return rx


def leer_registro(reg, signed=False, scale=1, descripcion=""):
    frame = bytes([SLAVE, 0x03, (reg >> 8) & 0xFF, reg & 0xFF, 0x00, 0x01])
    frame += crc16_modbus(frame)

    print("\n--------------------------------")
    print(f"LEER {descripcion}")
    print(f"Registro: {reg}")

    rx = enviar_frame(frame)

    if not rx:
        return None
    if len(rx) >= 3 and rx[1] & 0x80:
        print(f"EXCEPCIÓN MODBUS: código {rx[2]}")
        return None
    if len(rx) < 7:
        print("Respuesta incompleta")
        return None

    raw = int.from_bytes(rx[3:5], byteorder="big", signed=signed)
    value = raw / scale

    print(f"RAW: {raw}")
    print(f"VALOR: {value}")
    return value


def escribir_registro(reg, value, descripcion=""):
    frame = bytes([
        SLAVE, 0x06,
        (reg >> 8) & 0xFF,
        reg & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF
    ])
    frame += crc16_modbus(frame)

    print("\n--------------------------------")
    print(f"ESCRIBIR {descripcion}")
    print(f"Registro: {reg}")
    print(f"Valor: {value}")

    rx = enviar_frame(frame)

    if not rx:
        return False
    if len(rx) >= 3 and rx[1] & 0x80:
        print(f"EXCEPCIÓN MODBUS: código {rx[2]}")
        return False

    print("Comando enviado.")
    return True


def leer_status():
    value = leer_registro(REG_STATUS, False, 1, "Communication Status")
    if value == 7:
        print("HVAC READY")
    elif value == 0:
        print("HVAC NOT READY")
    elif value is not None:
        print("Estado intermedio")
    return value


def leer_unit_type():
    return leer_registro(REG_UNIT_TYPE, False, 1, "Unit Type")


def leer_onoff():
    value = leer_registro(REG_ONOFF, False, 1, "ON/OFF")
    if value == 1:
        print("HVAC ON")
    elif value == 0:
        print("HVAC OFF")
    return value


def encender():
    return escribir_registro(REG_ONOFF, 1, "HVAC ON")


def apagar():
    return escribir_registro(REG_ONOFF, 0, "HVAC OFF")


def leer_modo():
    value = leer_registro(REG_MODE, False, 1, "Operating Mode")
    modos = {0: "Auto", 1: "Cool", 2: "Dry", 3: "Fan", 4: "Heat"}
    if value is not None:
        print("Modo:", modos.get(int(value), "Desconocido"))
    return value


def modo_cool():
    return escribir_registro(REG_MODE, 1, "Modo COOL")


def modo_auto():
    return escribir_registro(REG_MODE, 0, "Modo AUTO")


def leer_fan():
    value = leer_registro(REG_FAN, False, 1, "Fan Speed")
    fans = {0: "Auto", 1: "Low", 2: "Medium", 3: "High"}
    if value is not None:
        print("Fan:", fans.get(int(value), "Desconocido"))
    return value


def cambiar_fan():
    print("\n0=Auto | 1=Low | 2=Medium | 3=High")
    fan = input("Seleccione fan: ").strip()

    if fan not in ["0", "1", "2", "3"]:
        print("Fan inválido.")
        return False

    return escribir_registro(REG_FAN, int(fan), f"Fan {fan}")


def leer_setpoint():
    return leer_registro(REG_SETPOINT, False, 10, "Setpoint activo °C")


def cambiar_setpoint():
    temp = input("Ingrese setpoint °C. Ejemplo 24.5: ").strip()

    try:
        temp_c = float(temp)
    except ValueError:
        print("Temperatura inválida.")
        return False

    value = int(round(temp_c * 10))
    return escribir_registro(REG_SETPOINT, value, f"Setpoint {temp_c:.1f} °C")


def leer_room_temp():
    return leer_registro(REG_ROOM_TEMP, False, 10, "Room Temperature °C")


def leer_error():
    return leer_registro(REG_ERROR, False, 1, "Indoor Error Code")


def leer_todo():
    leer_status()
    time.sleep(0.5)
    leer_unit_type()
    time.sleep(0.5)
    leer_onoff()
    time.sleep(0.5)
    leer_modo()
    time.sleep(0.5)
    leer_fan()
    time.sleep(0.5)
    leer_setpoint()
    time.sleep(0.5)
    leer_room_temp()
    time.sleep(0.5)
    leer_error()


def secuencia_cool_24_5():
    print("\nSecuencia: modo COOL + ON + setpoint 24.5 °C")
    confirmar = input("¿Enviar comandos? (s/n): ").strip().lower()

    if confirmar != "s":
        print("Cancelado.")
        return

    modo_cool()
    time.sleep(1)
    encender()
    time.sleep(1)
    escribir_registro(REG_SETPOINT, 245, "Setpoint 24.5 °C")


def menu():
    while True:
        print(f"""
=========================================
 TEST SAMSUNG HVAC RAW MODBUS
=========================================

Puerto : {PORT}
Serial : 9600,E,8,1
Slave  : {SLAVE}

Registros confirmados:
50 Status
52 ON/OFF
53 Mode
54 Fan
58 Setpoint activo
59 Room Temperature
63 Error

1. Leer Communication Status
2. Leer Unit Type
3. Leer ON/OFF
4. Encender HVAC
5. Apagar HVAC
6. Leer modo
7. Colocar modo COOL
8. Colocar modo AUTO
9. Leer fan
10. Cambiar fan
11. Leer setpoint activo
12. Cambiar setpoint
13. Leer room temperature
14. Leer error code
15. Leer todo
16. Secuencia COOL + ON + 24.5°C
0. Salir
""")

        op = input("Seleccione opción: ").strip()

        if op == "1":
            leer_status()
        elif op == "2":
            leer_unit_type()
        elif op == "3":
            leer_onoff()
        elif op == "4":
            encender()
        elif op == "5":
            apagar()
        elif op == "6":
            leer_modo()
        elif op == "7":
            modo_cool()
        elif op == "8":
            modo_auto()
        elif op == "9":
            leer_fan()
        elif op == "10":
            cambiar_fan()
        elif op == "11":
            leer_setpoint()
        elif op == "12":
            cambiar_setpoint()
        elif op == "13":
            leer_room_temp()
        elif op == "14":
            leer_error()
        elif op == "15":
            leer_todo()
        elif op == "16":
            secuencia_cool_24_5()
        elif op == "0":
            print("Saliendo.")
            break
        else:
            print("Opción inválida.")

        input("\nENTER para continuar...")


if __name__ == "__main__":
    menu()