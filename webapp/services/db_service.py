from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import json
import threading


# =========================================================
# RUTAS
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_DIR / "data"

DB_PATH = DATA_DIR / "maduracion.db"


# =========================================================
# LOCK
# =========================================================

_DB_LOCK = threading.RLock()


# =========================================================
# INICIALIZACIÓN
# =========================================================

def init_db():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            # Mejor comportamiento para lecturas de la web
            # mientras el programa principal escribe.
            conn.execute(
                "PRAGMA journal_mode=WAL;"
            )

            conn.execute(
                "PRAGMA synchronous=NORMAL;"
            )

            # =================================================
            # MEDICIONES
            # =================================================

            conn.execute("""
                CREATE TABLE IF NOT EXISTS mediciones (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    timestamp_utc TEXT NOT NULL,

                    sensor TEXT NOT NULL,

                    variable TEXT NOT NULL,

                    valor REAL,

                    unidad TEXT

                )
            """)

            # Índice principal para gráficas
            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_mediciones_sensor_variable_fecha

                ON mediciones(
                    sensor,
                    variable,
                    timestamp_utc
                )
            """)

            # =================================================
            # EVENTOS
            # =================================================

            conn.execute("""
                CREATE TABLE IF NOT EXISTS eventos (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    timestamp_utc TEXT NOT NULL,

                    tipo TEXT NOT NULL,

                    estado TEXT,

                    valor REAL,

                    detalle TEXT

                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_eventos_fecha

                ON eventos(
                    timestamp_utc
                )
            """)

            # =================================================
            # CICLOS CO2
            # =================================================

            conn.execute("""
                CREATE TABLE IF NOT EXISTS ciclos_co2 (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    inicio_utc TEXT NOT NULL,

                    fin_utc TEXT,

                    co2_low REAL,

                    co2_high REAL,

                    duracion_segundos REAL,

                    temperatura_media REAL,

                    humedad_media REAL,

                    c2h4_medio REAL,

                    estado TEXT NOT NULL DEFAULT 'ABIERTO'

                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_ciclos_co2_inicio

                ON ciclos_co2(
                    inicio_utc
                )
            """)
            # =================================================
            # PROCESOS DE MADURACIÓN
            # =================================================

            conn.execute("""
                CREATE TABLE IF NOT EXISTS procesos (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    inicio_utc TEXT NOT NULL,

                    fin_utc TEXT,

                    lote TEXT,

                    observaciones TEXT,

                    estado TEXT NOT NULL DEFAULT 'ACTIVO'

                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_procesos_estado

                ON procesos(
                    estado
                )
            """)


            conn.commit()


# =========================================================
# FECHA UTC
# =========================================================

def _utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def _normalizar_timestamp_utc(timestamp):
    """
    Normaliza cualquier timestamp recibido a ISO 8601 UTC.
    """

    if timestamp in [None, "", "None"]:
        return _utc_now()

    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(
            float(timestamp),
            tz=timezone.utc
        ).isoformat()

    texto = str(timestamp).strip()

    try:
        epoch = float(texto)
        return datetime.fromtimestamp(
            epoch,
            tz=timezone.utc
        ).isoformat()
    except (TypeError, ValueError):
        pass

    try:
        dt = datetime.fromisoformat(
            texto.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        ).isoformat()

    except (TypeError, ValueError):
        return _utc_now()


# =========================================================
# INSERTAR MEDICIÓN
# =========================================================

def guardar_medicion(
    sensor,
    variable,
    valor,
    unidad=None,
    timestamp_utc=None
):

    if valor in [None, "None", ""]:

        return False

    try:

        valor_float = float(valor)

    except (TypeError, ValueError):

        return False


    # Siempre normalizar, venga como epoch, ISO o None.
    timestamp_utc = _normalizar_timestamp_utc(
        timestamp_utc
    )


    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            conn.execute("""
                INSERT INTO mediciones (

                    timestamp_utc,
                    sensor,
                    variable,
                    valor,
                    unidad

                )

                VALUES (?, ?, ?, ?, ?)

            """, (

                timestamp_utc,
                str(sensor),
                str(variable),
                valor_float,
                str(unidad) if unidad is not None else None

            ))

            conn.commit()

    return True


# =========================================================
# INSERTAR EVENTO
# =========================================================

def guardar_evento(
    tipo,
    estado=None,
    valor=None,
    detalle=None,
    timestamp_utc=None
):

    # Mantener todos los eventos en ISO 8601 UTC.
    timestamp_utc = _normalizar_timestamp_utc(
        timestamp_utc
    )


    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            conn.execute("""
                INSERT INTO eventos (

                    timestamp_utc,
                    tipo,
                    estado,
                    valor,
                    detalle

                )

                VALUES (?, ?, ?, ?, ?)

            """, (

                timestamp_utc,
                str(tipo),
                str(estado) if estado is not None else None,
                valor,
                str(detalle) if detalle is not None else None

            ))

            conn.commit()


# =========================================================
# EXTRAER PAYLOAD
# =========================================================

def _extraer_payload(payload):

    if payload is None:

        return None


    if isinstance(payload, str):

        try:

            payload = json.loads(payload)

        except Exception:

            return None


    if not isinstance(payload, dict):

        return None


    datos = payload.get(
        "d",
        []
    )


    if not datos:

        return None


    registro = datos[0]

    if not isinstance(registro, dict):

        return None


    return registro


# =========================================================
# GUARDAR LOS SENSORES DEL CICLO
# =========================================================

def guardar_sensores(datos):

    """
    Guarda una fotografía completa de los sensores.

    Espera:
        sensor_CT01CO2
        sensor_THT03R
        sensor_PT21A01
        sensor_C2H4
        sensor_CWT
    """

    init_db()


    # =====================================================
    # MAPA
    # =====================================================

    sensores = {

        "sensor_CT01CO2": {

            "sensor": "CT01CO2",

            "variables": [
                "co2"
            ]

        },


        "sensor_THT03R": {

            "sensor": "THT03R",

            "variables": [
                "temperatura",
                "humedad"
            ]

        },


        "sensor_PT21A01": {

            "sensor": "PT21A01",

            "variables": [
                "temperatura",
                "resistencia"
            ]

        },


        "sensor_C2H4": {

            "sensor": "C2H4",

            "variables": [
                "humedad",
                "temperatura",
                "c2h4"
            ]

        },


        "sensor_CWT": {

            "sensor": "CWT",

            "variables": [
                "temperatura_ch1"
            ]

        }

    }


    insertadas = 0


    for clave, definicion in sensores.items():

        payload = datos.get(
            clave
        )


        registro = _extraer_payload(
            payload
        )


        if registro is None:

            continue


        valores = registro.get(
            "v",
            []
        )


        unidades = registro.get(
            "u",
            []
        )


        timestamp = registro.get(
            "t"
        )


        variables = definicion[
            "variables"
        ]


        for indice, variable in enumerate(variables):

            if indice >= len(valores):

                continue


            valor = valores[indice]


            unidad = (

                unidades[indice]

                if indice < len(unidades)

                else None

            )


            if guardar_medicion(

                sensor=definicion["sensor"],

                variable=variable,

                valor=valor,

                unidad=unidad,

                timestamp_utc=timestamp

            ):

                insertadas += 1


    return insertadas

def consultar_historico(
    sensor,
    variable,
    desde_utc,
    hasta_utc
):
    """
    Consulta histórica usando intervalo [desde, hasta).

    desde_utc incluido.
    hasta_utc excluido.
    """

    init_db()

    with _DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:

            conn.row_factory = sqlite3.Row

            filas = conn.execute(
                """
                SELECT
                    timestamp_utc,
                    valor,
                    unidad
                FROM mediciones
                WHERE sensor = ?
                  AND variable = ?
                  AND timestamp_utc >= ?
                  AND timestamp_utc < ?
                ORDER BY timestamp_utc ASC
                """,
                (
                    sensor,
                    variable,
                    desde_utc,
                    hasta_utc
                )
            ).fetchall()

    return [
        {
            "timestamp": fila["timestamp_utc"],
            "valor": fila["valor"],
            "unidad": fila["unidad"]
        }
        for fila in filas
    ]
    
def obtener_ultimo_valor(
    sensor,
    variable
):
    """
    Devuelve la última medición disponible
    para un sensor/variable.
    """

    init_db()

    with _DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:

            conn.row_factory = sqlite3.Row

            fila = conn.execute(
                """
                SELECT
                    timestamp_utc,
                    valor,
                    unidad
                FROM mediciones
                WHERE sensor = ?
                  AND variable = ?
                ORDER BY timestamp_utc DESC
                LIMIT 1
                """,
                (
                    sensor,
                    variable
                )
            ).fetchone()

    if fila is None:
        return None

    return {
        "timestamp_utc": fila["timestamp_utc"],
        "valor": fila["valor"],
        "unidad": fila["unidad"]
    }
    
    
def iniciar_proceso(
    lote=None,
    observaciones=None
):
    """
    Inicia un nuevo proceso de maduración.

    Solo puede existir un proceso ACTIVO.
    """

    init_db()

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            activo = conn.execute("""
                SELECT id
                FROM procesos
                WHERE estado = 'ACTIVO'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if activo is not None:

                return {
                    "ok": False,
                    "mensaje": (
                        "Ya existe un proceso activo."
                    ),
                    "id": activo[0]
                }

            inicio_utc = _utc_now()

            cursor = conn.execute("""
                INSERT INTO procesos (
                    inicio_utc,
                    lote,
                    observaciones,
                    estado
                )
                VALUES (?, ?, ?, 'ACTIVO')
            """, (
                inicio_utc,
                lote,
                observaciones
            ))

            conn.commit()

            return {
                "ok": True,
                "id": cursor.lastrowid,
                "inicio_utc": inicio_utc
            }


def obtener_proceso_activo():

    init_db()

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            conn.row_factory = sqlite3.Row

            fila = conn.execute("""
                SELECT
                    id,
                    inicio_utc,
                    fin_utc,
                    lote,
                    observaciones,
                    estado
                FROM procesos
                WHERE estado = 'ACTIVO'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

    if fila is None:
        return None

    return dict(fila)


def finalizar_proceso():

    init_db()

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            fila = conn.execute("""
                SELECT id
                FROM procesos
                WHERE estado = 'ACTIVO'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if fila is None:

                return {
                    "ok": False,
                    "mensaje": (
                        "No existe un proceso activo."
                    )
                }

            proceso_id = fila[0]

            fin_utc = _utc_now()

            conn.execute("""
                UPDATE procesos
                SET
                    fin_utc = ?,
                    estado = 'FINALIZADO'
                WHERE id = ?
            """, (
                fin_utc,
                proceso_id
            ))

            conn.commit()

            return {
                "ok": True,
                "id": proceso_id,
                "fin_utc": fin_utc
            }
            
def _obtener_proceso_activo_id():
    """
    Devuelve el ID del proceso activo.
    """

    init_db()

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            fila = conn.execute("""
                SELECT id
                FROM procesos
                WHERE estado = 'ACTIVO'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

    if fila is None:
        return None

    return fila[0]


def _asegurar_proceso_id_ciclos():
    """
    Agrega proceso_id a ciclos_co2 si todavía
    no existe en una base creada anteriormente.
    """

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            columnas = conn.execute(
                """
                PRAGMA table_info(ciclos_co2)
                """
            ).fetchall()

            nombres = [
                columna[1]
                for columna in columnas
            ]

            if "proceso_id" not in nombres:

                conn.execute("""
                    ALTER TABLE ciclos_co2
                    ADD COLUMN proceso_id INTEGER
                """)

                conn.commit()


def procesar_ciclo_co2(
    valor_co2,
    timestamp_utc,
    co2_low,
    co2_high
):
    """
    Detecta automáticamente ciclos CO2 LOW -> HIGH.

    El ciclo comienza cuando:
        CO2 <= co2_low

    El ciclo finaliza cuando:
        CO2 >= co2_high

    Solo funciona si hay proceso de maduración activo.
    """

    init_db()

    _asegurar_proceso_id_ciclos()

    try:

        valor_co2 = float(
            valor_co2
        )

        co2_low = float(
            co2_low
        )

        co2_high = float(
            co2_high
        )

    except (TypeError, ValueError):

        return {
            "evento": None
        }


    timestamp_utc = (
        _normalizar_timestamp_utc(
            timestamp_utc
        )
    )


    proceso_id = (
        _obtener_proceso_activo_id()
    )


    if proceso_id is None:

        return {
            "evento": None
        }


    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            conn.row_factory = sqlite3.Row


            # =============================================
            # ¿HAY CICLO ABIERTO?
            # =============================================

            ciclo = conn.execute(
                """
                SELECT
                    id,
                    inicio_utc,
                    co2_low,
                    co2_high
                FROM ciclos_co2
                WHERE proceso_id = ?
                  AND estado = 'ABIERTO'
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    proceso_id,
                )
            ).fetchone()


            # =============================================
            # NO HAY CICLO:
            # ABRIR SI CO2 <= LOW
            # =============================================

            if ciclo is None:

                if valor_co2 <= co2_low:

                    cursor = conn.execute(
                        """
                        INSERT INTO ciclos_co2 (
                            proceso_id,
                            inicio_utc,
                            co2_low,
                            co2_high,
                            estado
                        )
                        VALUES (?, ?, ?, ?, 'ABIERTO')
                        """,
                        (
                            proceso_id,
                            timestamp_utc,
                            co2_low,
                            co2_high
                        )
                    )

                    conn.commit()

                    return {
                        "evento": "CICLO_ABIERTO",
                        "id": cursor.lastrowid,
                        "proceso_id": proceso_id,
                        "inicio_utc": timestamp_utc
                    }


                return {
                    "evento": None
                }


            # =============================================
            # CICLO ABIERTO:
            # CERRAR SI CO2 >= HIGH
            # =============================================

            if valor_co2 >= co2_high:

                ciclo_id = ciclo["id"]

                inicio_utc = datetime.fromisoformat(
                    str(
                        ciclo["inicio_utc"]
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )

                fin_utc = datetime.fromisoformat(
                    str(
                        timestamp_utc
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )

                duracion_segundos = (
                    fin_utc -
                    inicio_utc
                ).total_seconds()


                # =========================================
                # PROMEDIOS DURANTE EL CICLO
                # =========================================

                temperatura = conn.execute(
                    """
                    SELECT AVG(valor)
                    FROM mediciones
                    WHERE sensor = 'THT03R'
                      AND variable = 'temperatura'
                      AND timestamp_utc >= ?
                      AND timestamp_utc <= ?
                    """,
                    (
                        ciclo["inicio_utc"],
                        timestamp_utc
                    )
                ).fetchone()[0]


                humedad = conn.execute(
                    """
                    SELECT AVG(valor)
                    FROM mediciones
                    WHERE sensor = 'THT03R'
                      AND variable = 'humedad'
                      AND timestamp_utc >= ?
                      AND timestamp_utc <= ?
                    """,
                    (
                        ciclo["inicio_utc"],
                        timestamp_utc
                    )
                ).fetchone()[0]


                c2h4 = conn.execute(
                    """
                    SELECT AVG(valor)
                    FROM mediciones
                    WHERE sensor = 'C2H4'
                      AND variable = 'c2h4'
                      AND timestamp_utc >= ?
                      AND timestamp_utc <= ?
                    """,
                    (
                        ciclo["inicio_utc"],
                        timestamp_utc
                    )
                ).fetchone()[0]


                conn.execute(
                    """
                    UPDATE ciclos_co2

                    SET
                        fin_utc = ?,
                        duracion_segundos = ?,
                        temperatura_media = ?,
                        humedad_media = ?,
                        c2h4_medio = ?,
                        estado = 'CERRADO'

                    WHERE id = ?
                    """,
                    (
                        timestamp_utc,
                        duracion_segundos,
                        temperatura,
                        humedad,
                        c2h4,
                        ciclo_id
                    )
                )

                conn.commit()


                return {
                    "evento": "CICLO_CERRADO",
                    "id": ciclo_id,
                    "proceso_id": proceso_id,
                    "inicio_utc":
                        ciclo["inicio_utc"],
                    "fin_utc":
                        timestamp_utc,
                    "duracion_segundos":
                        duracion_segundos
                }


    return {
        "evento": None
    }
    
def obtener_ciclos_proceso(
    proceso_id
):

    init_db()

    _asegurar_proceso_id_ciclos()

    with _DB_LOCK:

        with sqlite3.connect(DB_PATH) as conn:

            conn.row_factory = sqlite3.Row

            filas = conn.execute(
                """
                SELECT
                    id,
                    inicio_utc,
                    fin_utc,
                    co2_low,
                    co2_high,
                    duracion_segundos,
                    temperatura_media,
                    humedad_media,
                    c2h4_medio,
                    estado

                FROM ciclos_co2

                WHERE proceso_id = ?

                ORDER BY inicio_utc ASC
                """,
                (
                    proceso_id,
                )
            ).fetchall()

    return [
        dict(fila)
        for fila in filas
    ]