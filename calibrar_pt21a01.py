#!/usr/bin/env python3
import os
import csv
import json
import time
import statistics
import minimalmodbus
import serial
from datetime import datetime

# ==============================
# CONFIGURACIÓN
# ==============================

PORT = "/dev/ttyS0"
SLAVE_ID = 3

BAUDRATE = 9600
BYTESIZE = 8
PARITY = serial.PARITY_NONE
STOPBITS = 1
TIMEOUT = 1.5

CSV_FILE = "calibracion_pt21a01.csv"
CAL_FILE = "calibracion_pt21a01.json"

# PT21A01
REG_TEMP = 0       # 0x0000 temperatura
REG_RES = 32       # 0x0020 resistencia PT100
DECIMALS = 1


# ==============================
# MODBUS
# ==============================

def crear_instrumento():
    inst = minimalmodbus.Instrument(PORT, SLAVE_ID)
    inst.serial.baudrate = BAUDRATE
    inst.serial.bytesize = BYTESIZE
    inst.serial.parity = PARITY
    inst.serial.stopbits = STOPBITS
    inst.serial.timeout = TIMEOUT
    inst.serial.inter_byte_timeout = 0.2
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = False
    return inst


def leer_pt21a01():
    inst = crear_instrumento()

    temp = inst.read_register(
        REG_TEMP,
        DECIMALS,
        functioncode=3,
        signed=True
    )

    time.sleep(0.15)

    resistencia = inst.read_register(
        REG_RES,
        DECIMALS,
        functioncode=3,
        signed=False
    )

    return round(temp, 2), round(resistencia, 2)


# ==============================
# DATOS / CSV
# ==============================

def hora_rtc_sistema():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def guardar_muestra(temp_pt21, resistencia, temp_patron):
    existe = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not existe:
            writer.writerow([
                "fecha_hora",
                "temp_pt21a01",
                "resistencia_ohm",
                "temp_patron",
                "error_patron_menos_pt21"
            ])

        writer.writerow([
            hora_rtc_sistema(),
            temp_pt21,
            resistencia,
            temp_patron,
            round(temp_patron - temp_pt21, 3)
        ])


def cargar_muestras():
    muestras = []

    if not os.path.exists(CSV_FILE):
        return muestras

    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            muestras.append({
                "temp_pt21a01": float(row["temp_pt21a01"]),
                "temp_patron": float(row["temp_patron"])
            })

    return muestras


# ==============================
# REGRESIÓN LINEAL
# ==============================

def calcular_regresion(muestras):
    n = len(muestras)

    if n < 2:
        raise ValueError("Se necesitan mínimo 2 puntos para calcular la recta.")

    x = [m["temp_pt21a01"] for m in muestras]
    y = [m["temp_patron"] for m in muestras]

    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    numerador = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominador = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominador == 0:
        raise ValueError("Los valores del PT21A01 no tienen variación.")

    m = numerador / denominador
    b = y_mean - (m * x_mean)

    errores = []
    for i in range(n):
        estimada = (m * x[i]) + b
        error = y[i] - estimada
        errores.append(error)

    mae = statistics.mean(abs(e) for e in errores)
    error_max = max(abs(e) for e in errores)
    std = statistics.stdev(errores) if len(errores) > 1 else 0.0

    resultado = {
        "m": round(m, 8),
        "b": round(b, 8),
        "numero_muestras": n,
        "mae": round(mae, 4),
        "desviacion_std": round(std, 4),
        "error_max": round(error_max, 4),
        "fecha_calibracion": hora_rtc_sistema()
    }

    with open(CAL_FILE, "w") as f:
        json.dump(resultado, f, indent=4)

    return resultado


def cargar_calibracion():
    if not os.path.exists(CAL_FILE):
        return None

    with open(CAL_FILE, "r") as f:
        return json.load(f)


def aplicar_calibracion(temp_pt21, calibracion):
    m = float(calibracion["m"])
    b = float(calibracion["b"])
    return round((m * temp_pt21) + b, 2)


# ==============================
# MENÚ
# ==============================

def menu_calibrar():
    print("\n=== CALIBRACIÓN PT21A01 ===")
    print("Recomendación: tomar varios puntos entre 15 °C y 22 °C.\n")

    while True:
        try:
            temp_pt21, resistencia = leer_pt21a01()

            print(f"\nFecha/hora RTC: {hora_rtc_sistema()}")
            print(f"PT21A01 temperatura: {temp_pt21} °C")
            print(f"PT100 resistencia:   {resistencia} Ω")

            dato = input("Ingrese temperatura patrón en °C ('q' para salir): ").strip()

            if dato.lower() == "q":
                break

            temp_patron = float(dato)

            guardar_muestra(temp_pt21, resistencia, temp_patron)

            print("Muestra guardada.")

            muestras = cargar_muestras()

            if len(muestras) >= 2:
                cal = calcular_regresion(muestras)

                print("\n--- ECUACIÓN DE CALIBRACIÓN ---")
                print(f"T_calibrada = {cal['m']} * T_PT21A01 + {cal['b']}")
                print(f"Muestras: {cal['numero_muestras']}")
                print(f"MAE: {cal['mae']} °C")
                print(f"Desviación estándar: {cal['desviacion_std']} °C")
                print(f"Error máximo: {cal['error_max']} °C")

        except Exception as e:
            print(f"Error en calibración: {type(e).__name__}: {e}")


def menu_medir():
    print("\n=== MEDICIÓN CALIBRADA PT21A01 ===")

    calibracion = cargar_calibracion()

    if not calibracion:
        print("No existe archivo de calibración. Primero ejecute 'Calibrar'.")
        return

    print(f"Ecuación: T_calibrada = {calibracion['m']} * T_PT21A01 + {calibracion['b']}")
    print("Presione Ctrl+C para salir.\n")

    try:
        while True:
            temp_pt21, resistencia = leer_pt21a01()
            temp_calibrada = aplicar_calibracion(temp_pt21, calibracion)

            print(
                f"{hora_rtc_sistema()} | "
                f"PT21A01={temp_pt21} °C | "
                f"Calibrada={temp_calibrada} °C | "
                f"R={resistencia} Ω"
            )

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nSaliendo de medición.")


def main():
    while True:
        print("""
===============================
   CALIBRADOR PT21A01 - MDFR
===============================

1. Calibrar con sensor patrón
2. Medir con calibración aplicada
3. Ver calibración actual
4. Ver archivo de muestras
0. Salir
""")

        op = input("Seleccione opción: ").strip()

        if op == "1":
            menu_calibrar()

        elif op == "2":
            menu_medir()

        elif op == "3":
            cal = cargar_calibracion()
            if cal:
                print(json.dumps(cal, indent=4))
            else:
                print("No hay calibración guardada.")

        elif op == "4":
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, "r") as f:
                    print(f.read())
            else:
                print("No hay muestras guardadas.")

        elif op == "0":
            print("Saliendo.")
            break

        else:
            print("Opción no válida.")


if __name__ == "__main__":
    main()