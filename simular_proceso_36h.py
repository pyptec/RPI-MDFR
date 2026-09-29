from datetime import datetime, timedelta, timezone
import math
import sqlite3
import subprocess

from webapp.services import db_service


# =========================================================
# CONFIGURACIÓN
# =========================================================

DURACION_HORAS = 36

# Para representar bien una purga de máximo 12 minutos
INTERVALO_MINUTOS = 1

CO2_LOW = 3000.0
CO2_HIGH = 9000.0

PURGA_MAX_MINUTOS = 12

LOTE_SIMULACION = "SIM-36H-CICLOS"

OBSERVACIONES = (
    "Simulación ficticia de 36 horas "
    "para validación de ciclos CO2, "
    "extractor y aire fresco."
)


# =========================================================
# PERFIL DE LOS 4 CICLOS
# =========================================================
#
# Funcionamiento simulado:
#
# LOW
#   ↓
# acumulación CO2
#   ↓
# HIGH >= 9000 ppm
#   ↓
# PURGA
#   extractor ON
#   aire_fresco ON
#   ↓
# CO2 <= 3000 ppm
#   ↓
# extractor OFF
# aire_fresco OFF
#
# Ninguna purga supera 12 minutos.
# =========================================================

CICLOS = [

    {
        "inicio_low_h": 0.0,
        "high_h": 3.0,
        "purga_minutos": 8,
        "co2_inicio": 2500,
        "co2_high": 9200,
        "co2_fin": 2800,
    },

    {
        "inicio_low_h": 8.0,
        "high_h": 12.0,
        "purga_minutos": 10,
        "co2_inicio": 2600,
        "co2_high": 9300,
        "co2_fin": 2900,
    },

    {
        "inicio_low_h": 17.0,
        "high_h": 22.0,
        "purga_minutos": 12,
        "co2_inicio": 2500,
        "co2_high": 9100,
        "co2_fin": 2950,
    },

    {
        "inicio_low_h": 27.0,
        "high_h": 34.0,
        "purga_minutos": 11,
        "co2_inicio": 2400,
        "co2_high": 9400,
        "co2_fin": 2850,
    },
]


# =========================================================
# VALIDAR CONFIGURACIÓN
# =========================================================

def validar_perfil_simulacion():

    for numero, ciclo in enumerate(
        CICLOS,
        start=1
    ):

        purga_minutos = float(
            ciclo["purga_minutos"]
        )

        co2_fin = float(
            ciclo["co2_fin"]
        )

        if purga_minutos > PURGA_MAX_MINUTOS:

            raise ValueError(
                f"Ciclo {numero}: "
                f"purga={purga_minutos} min "
                f"supera máximo de "
                f"{PURGA_MAX_MINUTOS} min."
            )

        if co2_fin > CO2_LOW:

            raise ValueError(
                f"Ciclo {numero}: "
                f"CO2 final={co2_fin} ppm "
                f"no alcanza LOW="
                f"{CO2_LOW} ppm."
            )


# =========================================================
# INTERPOLACIÓN
# =========================================================

def interpolar(
    x,
    x0,
    y0,
    x1,
    y1
):

    if x1 == x0:

        return float(
            y1
        )

    proporcion = (
        (x - x0)
        /
        (x1 - x0)
    )

    return (
        float(y0)
        +
        (
            float(y1)
            -
            float(y0)
        )
        *
        proporcion
    )


# =========================================================
# CALCULAR CO2
# =========================================================

def calcular_co2(
    hora
):

    # Entre ciclos se mantiene por encima de LOW
    # para evitar abrir ciclos accidentalmente.

    valor_espera = 4500.0


    for ciclo in CICLOS:

        inicio = float(
            ciclo[
                "inicio_low_h"
            ]
        )

        high = float(
            ciclo[
                "high_h"
            ]
        )

        purga_horas = (
            float(
                ciclo[
                    "purga_minutos"
                ]
            )
            /
            60.0
        )

        fin_purga = (
            high
            +
            purga_horas
        )


        # -------------------------------------------------
        # ACUMULACIÓN LOW -> HIGH
        # -------------------------------------------------

        if (
            inicio
            <= hora
            <= high
        ):

            return interpolar(
                hora,
                inicio,
                ciclo[
                    "co2_inicio"
                ],
                high,
                ciclo[
                    "co2_high"
                ]
            )


        # -------------------------------------------------
        # PURGA HIGH -> LOW
        #
        # Durante este tiempo:
        #
        # extractor = ON
        # aire_fresco = ON
        #
        # -------------------------------------------------

        if (
            high
            < hora
            <= fin_purga
        ):

            return interpolar(
                hora,
                high,
                ciclo[
                    "co2_high"
                ],
                fin_purga,
                ciclo[
                    "co2_fin"
                ]
            )


    return valor_espera


# =========================================================
# ACTUADORES FICTICIOS
# =========================================================

def calcular_actuadores(
    hora
):

    extractor = 0
    aire_fresco = 0


    for ciclo in CICLOS:

        high = float(
            ciclo[
                "high_h"
            ]
        )

        fin_purga = (
            high
            +
            (
                float(
                    ciclo[
                        "purga_minutos"
                    ]
                )
                /
                60.0
            )
        )


        if (
            high
            <= hora
            <= fin_purga
        ):

            extractor = 1
            aire_fresco = 1

            break


    return {
        "extractor":
            extractor,

        "aire_fresco":
            aire_fresco
    }


# =========================================================
# TEMPERATURA
# =========================================================

def calcular_temperatura(
    hora
):

    return round(
        19.0
        +
        0.8
        *
        math.sin(
            hora
            /
            3.0
        ),
        1
    )


# =========================================================
# HUMEDAD
# =========================================================

def calcular_humedad(
    hora
):

    return round(
        87.0
        +
        2.0
        *
        math.sin(
            hora
            /
            4.0
        ),
        1
    )


# =========================================================
# C2H4
# =========================================================

def calcular_c2h4(
    hora
):

    return round(
        min(
            150.0,
            5.0
            +
            hora
            *
            3.0
        ),
        1
    )


# =========================================================
# VERIFICAR QUE rpi-mdfr.py ESTÉ DETENIDO
# =========================================================

def verificar_mdfr_detenido():

    resultado = subprocess.run(
        [
            "pgrep",
            "-af",
            "rpi-mdfr.py"
        ],
        capture_output=True,
        text=True
    )


    procesos = []

    for linea in (
        resultado
        .stdout
        .splitlines()
    ):

        linea = (
            linea.strip()
        )

        if not linea:

            continue

        if "pgrep" in linea:

            continue

        procesos.append(
            linea
        )


    if procesos:

        raise RuntimeError(
            "rpi-mdfr.py está ejecutándose.\n"
            "Deténgalo antes de ejecutar "
            "la simulación.\n\n"
            +
            "\n".join(
                procesos
            )
        )


# =========================================================
# VERIFICAR PROCESO ACTIVO
# =========================================================

def verificar_sin_proceso_activo():

    proceso = (
        db_service
        .obtener_proceso_activo()
    )


    if proceso is not None:

        raise RuntimeError(
            "Existe un proceso ACTIVO "
            f"id={proceso.get('id')}. "
            "Finalícelo primero desde la web."
        )


# =========================================================
# LIMPIAR SIMULACIÓN ANTERIOR
# =========================================================

def limpiar_simulacion_anterior():

    db_service.init_db()


    with sqlite3.connect(
        db_service.DB_PATH
    ) as conn:


        filas = conn.execute(
            """
            SELECT id
            FROM procesos
            WHERE lote = ?
            """,
            (
                LOTE_SIMULACION,
            )
        ).fetchall()


        ids = [
            fila[0]
            for fila in filas
        ]


        for proceso_id in ids:

            conn.execute(
                """
                DELETE FROM ciclos_co2
                WHERE proceso_id = ?
                """,
                (
                    proceso_id,
                )
            )


        conn.execute(
            """
            DELETE FROM procesos
            WHERE lote = ?
            """,
            (
                LOTE_SIMULACION,
            )
        )


        conn.commit()


# =========================================================
# CREAR PROCESO FICTICIO
# =========================================================

def crear_proceso_simulado(
    inicio_utc
):

    resultado = (
        db_service
        .iniciar_proceso(
            lote=
                LOTE_SIMULACION,

            observaciones=
                OBSERVACIONES
        )
    )


    if not resultado.get(
        "ok"
    ):

        raise RuntimeError(
            resultado.get(
                "mensaje",
                "No se pudo crear proceso."
            )
        )


    proceso_id = (
        resultado[
            "id"
        ]
    )


    # iniciar_proceso usa hora real.
    # Movemos solo el inicio del proceso
    # 36 horas hacia atrás.

    with sqlite3.connect(
        db_service.DB_PATH
    ) as conn:

        conn.execute(
            """
            UPDATE procesos

            SET
                inicio_utc = ?,
                observaciones = ?

            WHERE id = ?
            """,
            (
                inicio_utc.isoformat(),
                OBSERVACIONES,
                proceso_id
            )
        )


        conn.commit()


    return proceso_id


# =========================================================
# GUARDAR MEDICIONES
# =========================================================

def guardar_mediciones(
    timestamp,
    co2,
    temperatura,
    humedad,
    c2h4,
    extractor,
    aire_fresco
):

    ts = (
        timestamp
        .isoformat()
    )


    # -----------------------------------------------------
    # CO2
    # -----------------------------------------------------

    db_service.guardar_medicion(
        sensor=
            "CT01CO2",

        variable=
            "co2",

        valor=
            co2,

        unidad=
            "ppm",

        timestamp_utc=
            ts
    )


    # -----------------------------------------------------
    # TEMPERATURA
    # -----------------------------------------------------

    db_service.guardar_medicion(
        sensor=
            "THT03R",

        variable=
            "temperatura",

        valor=
            temperatura,

        unidad=
            "°C",

        timestamp_utc=
            ts
    )


    # -----------------------------------------------------
    # HUMEDAD
    # -----------------------------------------------------

    db_service.guardar_medicion(
        sensor=
            "THT03R",

        variable=
            "humedad",

        valor=
            humedad,

        unidad=
            "%",

        timestamp_utc=
            ts
    )


    # -----------------------------------------------------
    # ETILENO
    # -----------------------------------------------------

    db_service.guardar_medicion(
        sensor=
            "C2H4",

        variable=
            "c2h4",

        valor=
            c2h4,

        unidad=
            "ppm",

        timestamp_utc=
            ts
    )


    # -----------------------------------------------------
    # ACTUADORES SIMULADOS
    #
    # IMPORTANTE:
    #
    # SIM_MDFR evita confundir estos estados
    # con los actuadores físicos reales DIOUSTOU.
    # -----------------------------------------------------

    db_service.guardar_medicion(
        sensor=
            "SIM_MDFR",

        variable=
            "extractor",

        valor=
            extractor,

        unidad=
            "estado",

        timestamp_utc=
            ts
    )


    db_service.guardar_medicion(
        sensor=
            "SIM_MDFR",

        variable=
            "aire_fresco",

        valor=
            aire_fresco,

        unidad=
            "estado",

        timestamp_utc=
            ts
    )


# =========================================================
# MOSTRAR RESULTADOS
# =========================================================

def mostrar_resultados(
    proceso_id
):

    ciclos = (
        db_service
        .obtener_ciclos_proceso(
            proceso_id
        )
    )


    print()

    print(
        "=" * 72
    )

    print(
        "RESULTADO DE LA SIMULACIÓN"
    )

    print(
        "=" * 72
    )


    print(
        f"Proceso ID: "
        f"{proceso_id}"
    )


    print(
        f"Ciclos registrados: "
        f"{len(ciclos)}"
    )


    print()


    for ciclo in ciclos:


        print(
            "Ciclo:",
            ciclo.get(
                "numero_ciclo"
            )
        )


        print(
            "  Estado:",
            ciclo.get(
                "estado"
            )
        )


        print(
            "  Inicio LOW:",
            ciclo.get(
                "inicio_utc"
            )
        )


        print(
            "  Inicio purga:",
            ciclo.get(
                "purga_inicio_utc"
            )
        )


        print(
            "  Fin purga:",
            ciclo.get(
                "purga_fin_utc"
            )
        )


        print(
            "  LOW -> HIGH:",
            ciclo.get(
                "duracion_segundos"
            ),
            "s"
        )


        print(
            "  Purga:",
            ciclo.get(
                "purga_duracion_segundos"
            ),
            "s"
        )


        print(
            "  Intervalo purgas:",
            ciclo.get(
                "intervalo_purgas_segundos"
            ),
            "s"
        )


        print(
            "  CO2 inicio purga:",
            ciclo.get(
                "co2_purge_start_ppm"
            )
        )


        print(
            "  CO2 fin purga:",
            ciclo.get(
                "co2_purge_end_ppm"
            )
        )


        print(
            "  Temp media:",
            ciclo.get(
                "temperatura_media"
            )
        )


        print(
            "  Hum media:",
            ciclo.get(
                "humedad_media"
            )
        )


        print(
            "  C2H4 medio:",
            ciclo.get(
                "c2h4_medio"
            )
        )


        print(
            "-" * 72
        )


# =========================================================
# SIMULACIÓN PRINCIPAL
# =========================================================

def main():

    print()

    print(
        "=" * 72
    )

    print(
        "SIMULADOR PROCESO MADURACIÓN - 36 HORAS"
    )

    print(
        "=" * 72
    )


    # -----------------------------------------------------
    # SEGURIDAD
    # -----------------------------------------------------

    verificar_mdfr_detenido()

    validar_perfil_simulacion()


    db_service.init_db()


    verificar_sin_proceso_activo()


    limpiar_simulacion_anterior()


    # -----------------------------------------------------
    # TIEMPO FICTICIO
    # -----------------------------------------------------

    fin_simulacion = (
        datetime.now(
            timezone.utc
        )
    )


    inicio_simulacion = (
        fin_simulacion
        -
        timedelta(
            hours=
                DURACION_HORAS
        )
    )


    proceso_id = (
        crear_proceso_simulado(
            inicio_simulacion
        )
    )


    print(
        f"Proceso simulado creado: "
        f"{proceso_id}"
    )


    print(
        f"Inicio ficticio: "
        f"{inicio_simulacion.isoformat()}"
    )


    print(
        f"Fin ficticio:    "
        f"{fin_simulacion.isoformat()}"
    )


    print()


    print(
        f"LOW={CO2_LOW:.0f} ppm | "
        f"HIGH={CO2_HIGH:.0f} ppm"
    )


    print(
        f"Purga máxima="
        f"{PURGA_MAX_MINUTOS} min"
    )


    print(
        "Durante PURGA: "
        "EXTRACTOR=ON + "
        "AIRE_FRESCO=ON"
    )


    print()


    # -----------------------------------------------------
    # CANTIDAD DE MUESTRAS
    # -----------------------------------------------------

    cantidad_muestras = (
        int(
            DURACION_HORAS
            *
            60
            /
            INTERVALO_MINUTOS
        )
        +
        1
    )


    eventos_detectados = []


    # =====================================================
    # BUCLE DE SIMULACIÓN
    # =====================================================

    for indice in range(
        cantidad_muestras
    ):


        minutos = (
            indice
            *
            INTERVALO_MINUTOS
        )


        hora = (
            minutos
            /
            60.0
        )


        timestamp = (
            inicio_simulacion
            +
            timedelta(
                minutes=
                    minutos
            )
        )


        # -------------------------------------------------
        # VARIABLES
        # -------------------------------------------------

        co2 = round(
            calcular_co2(
                hora
            ),
            1
        )


        temperatura = (
            calcular_temperatura(
                hora
            )
        )


        humedad = (
            calcular_humedad(
                hora
            )
        )


        c2h4 = (
            calcular_c2h4(
                hora
            )
        )


        actuadores = (
            calcular_actuadores(
                hora
            )
        )


        # -------------------------------------------------
        # GUARDAR HISTÓRICO
        # -------------------------------------------------

        guardar_mediciones(

            timestamp=
                timestamp,

            co2=
                co2,

            temperatura=
                temperatura,

            humedad=
                humedad,

            c2h4=
                c2h4,

            extractor=
                actuadores[
                    "extractor"
                ],

            aire_fresco=
                actuadores[
                    "aire_fresco"
                ]
        )


        # -------------------------------------------------
        # MÁQUINA REAL DE ESTADOS
        # -------------------------------------------------

        resultado = (
            db_service
            .procesar_ciclo_co2(

                valor_co2=
                    co2,

                timestamp_utc=
                    timestamp
                    .isoformat(),

                co2_low=
                    CO2_LOW,

                co2_high=
                    CO2_HIGH
            )
        )


        evento = (
            resultado.get(
                "evento"
            )
            if resultado
            else None
        )


        # -------------------------------------------------
        # MOSTRAR TRANSICIONES
        # -------------------------------------------------

        if evento:


            eventos_detectados.append(
                (
                    timestamp,
                    co2,
                    resultado
                )
            )


            if (
                evento
                ==
                "PURGA_INICIADA"
            ):

                estado_actuadores = (
                    "EXTRACTOR=ON | "
                    "AIRE_FRESCO=ON"
                )


            elif (
                evento
                ==
                "CICLO_COMPLETO"
            ):

                estado_actuadores = (
                    "EXTRACTOR=OFF | "
                    "AIRE_FRESCO=OFF"
                )


            else:

                estado_actuadores = (
                    "EXTRACTOR=OFF | "
                    "AIRE_FRESCO=OFF"
                )


            print(

                f"{timestamp.isoformat()} | "

                f"CO2="
                f"{co2:7.1f} ppm | "

                f"{evento} | "

                f"{estado_actuadores}"
            )


    # =====================================================
    # RESULTADOS
    # =====================================================

    print()


    print(
        f"Muestras generadas: "
        f"{cantidad_muestras}"
    )


    print(
        f"Transiciones detectadas: "
        f"{len(eventos_detectados)}"
    )


    mostrar_resultados(
        proceso_id
    )


    print()


    print(
        "Simulación terminada."
    )


    print(
        "El proceso queda ACTIVO para "
        "revisarlo desde la web."
    )


    print(
        "Mantenga rpi-mdfr.py detenido "
        "durante la revisión."
    )


    print(
        "Cuando termine, finalice el "
        "proceso desde la web."
    )


    print()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    main()