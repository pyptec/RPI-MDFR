from datetime import datetime, timedelta, timezone
import math
import sqlite3

from webapp.services import db_service


# =========================================================
# CONFIGURACIÓN DE LA SIMULACIÓN
# =========================================================

DURACION_HORAS = 36
INTERVALO_MINUTOS = 10

CO2_LOW = 3000.0
CO2_HIGH = 9000.0

LOTE_SIMULACION = "SIM-36H-CICLOS"

OBSERVACIONES = (
    "Simulación ficticia de 36 horas "
    "para validación de ciclos CO2."
)


# =========================================================
# PERFIL DE CO2
# =========================================================
#
# Cada ciclo tiene:
#
# inicio_low_h
# high_h
# fin_purga_h
#
# Ejemplo:
#
# 0 h     -> LOW
# 3 h     -> HIGH
# 3.5 h   -> LOW
#
# =========================================================

CICLOS = [

    {
        "inicio_low_h": 0.0,
        "high_h": 3.0,
        "fin_purga_h": 3.5,
        "co2_inicio": 2500,
        "co2_high": 9200,
        "co2_fin": 2500,
    },

    {
        "inicio_low_h": 8.0,
        "high_h": 12.0,
        "fin_purga_h": 12.5,
        "co2_inicio": 2600,
        "co2_high": 9300,
        "co2_fin": 2400,
    },

    {
        "inicio_low_h": 17.0,
        "high_h": 22.0,
        "fin_purga_h": 22.5,
        "co2_inicio": 2500,
        "co2_high": 9100,
        "co2_fin": 2600,
    },

    {
        "inicio_low_h": 27.0,
        "high_h": 34.0,
        "fin_purga_h": 34.5,
        "co2_inicio": 2400,
        "co2_high": 9400,
        "co2_fin": 2500,
    },
]


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
        return float(y1)

    proporcion = (
        (x - x0) /
        (x1 - x0)
    )

    return (
        float(y0) +
        (
            float(y1) -
            float(y0)
        ) *
        proporcion
    )


# =========================================================
# GENERAR CO2 PARA UNA HORA FICTICIA
# =========================================================

def calcular_co2(
    hora
):

    # Valor de espera entre ciclos.
    #
    # IMPORTANTE:
    # Debe quedar por encima de LOW para no abrir
    # accidentalmente un nuevo ciclo.

    valor_espera = 4500.0


    for ciclo in CICLOS:

        inicio = ciclo[
            "inicio_low_h"
        ]

        high = ciclo[
            "high_h"
        ]

        fin_purga = ciclo[
            "fin_purga_h"
        ]


        # ---------------------------------------------
        # SUBIDA LOW -> HIGH
        # ---------------------------------------------

        if (
            inicio <= hora <= high
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


        # ---------------------------------------------
        # PURGA HIGH -> LOW
        # ---------------------------------------------

        if (
            high < hora <= fin_purga
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
# VARIABLES AMBIENTALES FICTICIAS
# =========================================================

def calcular_temperatura(
    hora
):

    return round(
        19.0 +
        0.8 *
        math.sin(
            hora /
            3.0
        ),
        1
    )


def calcular_humedad(
    hora
):

    return round(
        87.0 +
        2.0 *
        math.sin(
            hora /
            4.0
        ),
        1
    )


def calcular_c2h4(
    hora
):

    # Curva sencilla ascendente durante
    # la maduración ficticia.

    return round(
        min(
            150.0,
            5.0 +
            hora *
            3.0
        ),
        1
    )


# =========================================================
# LIMPIAR PROCESO DE SIMULACIÓN ANTERIOR
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
# VERIFICAR QUE NO HAYA PROCESO ACTIVO
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


    # -----------------------------------------------------
    # iniciar_proceso() usa hora real.
    #
    # Para esta prueba movemos SOLAMENTE el inicio
    # del proceso ficticio 36 horas hacia atrás.
    # -----------------------------------------------------

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
# GUARDAR MEDICIONES FICTICIAS
# =========================================================

def guardar_mediciones(
    timestamp,
    co2,
    temperatura,
    humedad,
    c2h4
):

    ts = (
        timestamp
        .isoformat()
    )


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
        f"Proceso ID: {proceso_id}"
    )

    print(
        f"Ciclos registrados: {len(ciclos)}"
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


    db_service.init_db()


    verificar_sin_proceso_activo()


    limpiar_simulacion_anterior()


    # -----------------------------------------------------
    # Tiempo ficticio:
    #
    # termina aproximadamente AHORA.
    # comienza hace 36 horas.
    # -----------------------------------------------------

    fin_simulacion = (
        datetime.now(
            timezone.utc
        )
    )


    inicio_simulacion = (
        fin_simulacion -
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
        f"Proceso simulado creado: {proceso_id}"
    )

    print(
        f"Inicio ficticio: {inicio_simulacion.isoformat()}"
    )

    print(
        f"Fin ficticio:    {fin_simulacion.isoformat()}"
    )

    print()


    cantidad_muestras = (
        int(
            DURACION_HORAS *
            60 /
            INTERVALO_MINUTOS
        )
        +
        1
    )


    eventos_detectados = []


    for indice in range(
        cantidad_muestras
    ):

        minutos = (
            indice *
            INTERVALO_MINUTOS
        )


        hora = (
            minutos /
            60.0
        )


        timestamp = (
            inicio_simulacion +
            timedelta(
                minutes=
                    minutos
            )
        )


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


        # ---------------------------------------------
        # HISTÓRICO FICTICIO
        # ---------------------------------------------

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
                c2h4
        )


        # ---------------------------------------------
        # MISMA MÁQUINA DE ESTADOS DE PRODUCCIÓN
        # ---------------------------------------------

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


        if evento:

            eventos_detectados.append(
                (
                    timestamp,
                    co2,
                    resultado
                )
            )


            print(
                f"{timestamp.isoformat()} | "
                f"CO2={co2:7.1f} ppm | "
                f"{evento}"
            )


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
        "poder revisarlo desde la web."
    )

    print(
        "Cuando termine la revisión, "
        "finalícelo desde el botón de la página."
    )

    print()


if __name__ == "__main__":

    main()