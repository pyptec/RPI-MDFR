#!/usr/bin/env python3
import os
import csv
import json
import time
import statistics
import minimalmodbus
import serial
import select
import sys

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
REG_TEMP = 0
REG_RES = 32
DECIMALS = 1

# PROMEDIO
NUM_MUESTRAS = 10
DELAY_MUESTRAS = 1.0

# ==============================
# MODBUS
# ==============================

def crear_instrumento():

    inst = minimalmodbus.Instrument(
        PORT,
        SLAVE_ID
    )

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
# MONITOREO EN VIVO
# ==============================

def monitorear_hasta_enter():

    print("\n===================================")
    print(" MONITOREO PT21A01 EN VIVO")
    print("===================================")

    print(
        "\n"
        "Observe la temperatura.\n"
        "Cuando esté estable:\n"
        "- ENTER = capturar promedio\n"
        "- q + ENTER = salir\n"
    )

    while True:

        try:

            temp, resistencia = leer_pt21a01()

            print(
                f"\r{hora_rtc_sistema()} | "
                f"PT21A01={temp:.2f} °C | "
                f"R={resistencia:.2f} Ω      ",
                end="",
                flush=True
            )

            time.sleep(1)

            if sys.stdin in select.select(
                [sys.stdin],
                [],
                [],
                0
            )[0]:

                tecla = input().strip().lower()

                if tecla == "q":

                    print("\nSaliendo monitoreo.")

                    return None

                print("\n\nCapturando promedio...")

                return leer_pt21a01_promedio()

        except Exception as e:

            print(
                f"\nError monitoreo: "
                f"{type(e).__name__}: {e}"
            )

            time.sleep(1)

# ==============================
# PROMEDIO PT21A01
# ==============================

def leer_pt21a01_promedio(
    n=NUM_MUESTRAS,
    delay=DELAY_MUESTRAS
):

    temps = []
    resistencias = []

    print(f"\nTomando {n} muestras...\n")

    for i in range(n):

        temp, resistencia = leer_pt21a01()

        temps.append(temp)
        resistencias.append(resistencia)

        print(
            f"Muestra {i+1}/{n} -> "
            f"Temp={temp:.2f} °C | "
            f"R={resistencia:.2f} Ω"
        )

        time.sleep(delay)

    temp_prom = round(
        sum(temps) / len(temps),
        2
    )

    res_prom = round(
        sum(resistencias) / len(resistencias),
        2
    )

    temp_min = min(temps)
    temp_max = max(temps)

    variacion = round(
        temp_max - temp_min,
        3
    )

    print("\n===================================")
    print(" RESULTADO PROMEDIO")
    print("===================================")

    print(f"Temp promedio : {temp_prom:.2f} °C")

    print(f"R promedio    : {res_prom:.2f} Ω")

    print(f"Variación      : {variacion:.3f} °C")

    if variacion > 0.3:

        print(
            "ADVERTENCIA: "
            "temperatura poco estable."
        )

    return (
        temp_prom,
        res_prom,
        variacion
    )

# ==============================
# DATOS / CSV
# ==============================

def hora_rtc_sistema():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def guardar_muestra(
    temp_pt21,
    resistencia,
    temp_patron
):

    existe = os.path.exists(CSV_FILE)

    with open(
        CSV_FILE,
        "a",
        newline=""
    ) as f:

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
            round(
                temp_patron - temp_pt21,
                3
            )
        ])


def cargar_muestras():

    muestras = []

    if not os.path.exists(CSV_FILE):

        return muestras

    with open(CSV_FILE, "r") as f:

        reader = csv.DictReader(f)

        for row in reader:

            muestras.append({
                "temp_pt21a01": float(
                    row["temp_pt21a01"]
                ),
                "temp_patron": float(
                    row["temp_patron"]
                )
            })

    return muestras

# ==============================
# REGRESIÓN LINEAL
# ==============================

def calcular_regresion(muestras):

    n = len(muestras)

    if n < 2:

        raise ValueError(
            "Se necesitan mínimo "
            "2 puntos."
        )

    x = [
        m["temp_pt21a01"]
        for m in muestras
    ]

    y = [
        m["temp_patron"]
        for m in muestras
    ]

    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    numerador = sum(
        (x[i] - x_mean) *
        (y[i] - y_mean)
        for i in range(n)
    )

    denominador = sum(
        (x[i] - x_mean) ** 2
        for i in range(n)
    )

    if denominador == 0:

        raise ValueError(
            "No hay variación suficiente."
        )

    m = numerador / denominador

    b = y_mean - (m * x_mean)

    errores = []

    for i in range(n):

        estimada = (m * x[i]) + b

        error = y[i] - estimada

        errores.append(error)

    # ==============================
    # R CUADRADO
    # ==============================

    ss_res = sum(
        (y[i] - ((m * x[i]) + b)) ** 2
        for i in range(n)
    )

    ss_tot = sum(
        (y[i] - y_mean) ** 2
        for i in range(n)
    )

    if ss_tot == 0:
        r2 = 1.0
    else:
        r2 = 1 - (ss_res / ss_tot)

    mae = statistics.mean(
        abs(e) for e in errores
    )

    error_max = max(
        abs(e) for e in errores
    )

    std = (
        statistics.stdev(errores)
        if len(errores) > 1
        else 0.0
    )

    resultado = {

        "m": round(m, 8),

        "b": round(b, 8),

        "r2": round(r2, 6),

        "numero_muestras": n,

        "mae": round(mae, 4),

        "desviacion_std": round(std, 4),

        "error_max": round(error_max, 4),

        "fecha_calibracion": hora_rtc_sistema()
    }

    with open(CAL_FILE, "w") as f:

        json.dump(
            resultado,
            f,
            indent=4
        )

    return resultado


def cargar_calibracion():

    if not os.path.exists(CAL_FILE):

        return None

    with open(CAL_FILE, "r") as f:

        return json.load(f)


def aplicar_calibracion(
    temp_pt21,
    calibracion
):

    m = float(calibracion["m"])

    b = float(calibracion["b"])

    return round(
        (m * temp_pt21) + b,
        2
    )

# ==============================
# MENÚ CALIBRAR
# ==============================

def menu_calibrar():

    print("\n===================================")
    print(" CALIBRACIÓN PT21A01")
    print("===================================")

    print(
        "\n"
        "Recomendaciones:\n"
        "- Esperar estabilidad\n"
        "- RTD y patrón juntos\n"
        "- Usar varios puntos\n"
    )

    while True:

        try:

            resultado = monitorear_hasta_enter()

            if resultado is None:

                break

            temp_pt21, resistencia, variacion = resultado

            print(
                f"\nFecha RTC: "
                f"{hora_rtc_sistema()}"
            )

            print(
                f"PT21A01 promedio: "
                f"{temp_pt21} °C"
            )

            print(
                f"PT100 resistencia: "
                f"{resistencia} Ω"
            )

            dato = input(
                "\nIngrese temperatura "
                "patrón en °C "
                "('q' para salir): "
            ).strip()

            if dato.lower() == "q":

                break

            temp_patron = float(dato)

            guardar_muestra(
                temp_pt21,
                resistencia,
                temp_patron
            )

            print("\nMuestra guardada.")

            muestras = cargar_muestras()

            if len(muestras) >= 2:

                cal = calcular_regresion(
                    muestras
                )

                print("\n===================================")
                print(" ECUACIÓN DE CALIBRACIÓN")
                print("===================================")

                print(
                    f"\nT_calibrada = "
                    f"{cal['m']} * "
                    f"T_PT21A01 + "
                    f"{cal['b']}"
                )

                print(
                    f"\nR²: "
                    f"{cal['r2']}"
                )

                print(
                    f"\nMuestras: "
                    f"{cal['numero_muestras']}"
                )

                print(
                    f"MAE: "
                    f"{cal['mae']} °C"
                )

                print(
                    f"Desviación estándar: "
                    f"{cal['desviacion_std']} °C"
                )

                print(
                    f"Error máximo: "
                    f"{cal['error_max']} °C"
                )

        except Exception as e:

            print(
                f"\nError calibración: "
                f"{type(e).__name__}: {e}"
            )

# ==============================
# MENÚ MEDIR
# ==============================

def menu_medir():

    print(
        "\n==================================="
    )

    print(
        " MEDICIÓN CALIBRADA PT21A01"
    )

    print(
        "==================================="
    )

    calibracion = cargar_calibracion()

    if not calibracion:

        print(
            "No existe calibración."
        )

        return

    print(
        f"\nT_calibrada = "
        f"{calibracion['m']} * "
        f"T_PT21A01 + "
        f"{calibracion['b']}"
    )

    print(
        f"R² = {calibracion.get('r2', 'N/A')}"
    )

    print(
        "\nCtrl+C para salir.\n"
    )

    try:

        while True:

            temp_pt21, resistencia = (
                leer_pt21a01()
            )

            temp_calibrada = (
                aplicar_calibracion(
                    temp_pt21,
                    calibracion
                )
            )

            print(
                f"{hora_rtc_sistema()} | "
                f"PT21A01={temp_pt21} °C | "
                f"Calibrada={temp_calibrada} °C | "
                f"R={resistencia} Ω"
            )

            time.sleep(2)

    except KeyboardInterrupt:

        print(
            "\nSaliendo medición."
        )

# ==============================
# MAIN
# ==============================

def main():

    while True:

        print("""
===================================
   CALIBRADOR PT21A01 - MDFR
===================================

1. Calibrar con sensor patrón
2. Medir con calibración aplicada
3. Ver calibración actual
4. Ver archivo de muestras
0. Salir
""")

        op = input(
            "Seleccione opción: "
        ).strip()

        if op == "1":

            menu_calibrar()

        elif op == "2":

            menu_medir()

        elif op == "3":

            cal = cargar_calibracion()

            if cal:

                print(
                    json.dumps(
                        cal,
                        indent=4
                    )
                )

            else:

                print(
                    "No hay calibración."
                )

        elif op == "4":

            if os.path.exists(CSV_FILE):

                with open(CSV_FILE, "r") as f:

                    print(f.read())

            else:

                print(
                    "No hay muestras."
                )

        elif op == "0":

            print("Saliendo.")

            break

        else:

            print(
                "Opción no válida."
            )

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    main()