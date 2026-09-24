from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.services import db_service
from fastapi import FastAPI, Request, Query, HTTPException, Form

# =========================================================
# RUTAS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="PYP - Control Maduración Banano"
)


app.mount(
    "/static",
    StaticFiles(
        directory=str(BASE_DIR / "static")
    ),
    name="static"
)


# =========================================================
# ZONAS HORARIAS
# =========================================================

TZ_LOCAL = ZoneInfo(
    "America/Bogota"
)

TZ_UTC = ZoneInfo(
    "UTC"
)


# =========================================================
# UTILIDADES DE FECHA
# =========================================================

def local_a_utc_iso(fecha_texto):
    """
    Convierte una fecha/hora ingresada en hora Colombia
    a ISO 8601 UTC.

    Ejemplo:
        entrada:
        2026-09-23T16:00

        salida:
        2026-09-23T21:00:00+00:00
    """

    dt_local = datetime.fromisoformat(
        fecha_texto
    )

    dt_local = dt_local.replace(
        tzinfo=TZ_LOCAL
    )

    dt_utc = dt_local.astimezone(
        TZ_UTC
    )

    return dt_utc.isoformat()


def utc_a_colombia_iso(fecha_utc):
    """
    Convierte una fecha UTC almacenada en SQLite
    a hora Colombia.
    """

    dt = datetime.fromisoformat(
        str(fecha_utc).replace(
            "Z",
            "+00:00"
        )
    )

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=TZ_UTC
        )

    dt_colombia = dt.astimezone(
        TZ_LOCAL
    )

    return dt_colombia.isoformat()


# =========================================================
# INICIO
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def inicio(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# =========================================================
# GRÁFICAS
# =========================================================

@app.get(
    "/graficas",
    response_class=HTMLResponse
)
async def graficas(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="graficas.html",
        context={}
    )


# =========================================================
# API - VALORES ACTUALES
# =========================================================

@app.get(
    "/api/actual"
)
async def api_actual():

    variables = {

        "co2": (
            "CT01CO2",
            "co2"
        ),

        "temperatura": (
            "THT03R",
            "temperatura"
        ),

        "humedad": (
            "THT03R",
            "humedad"
        ),

        "c2h4": (
            "C2H4",
            "c2h4"
        ),

        "pt100": (
            "PT21A01",
            "temperatura"
        ),

        "pt1000": (
            "CWT",
            "temperatura_ch1"
        )
    }

    resultado = {}

    for nombre, (
        sensor,
        variable
    ) in variables.items():

        dato = db_service.obtener_ultimo_valor(
            sensor=sensor,
            variable=variable
        )

        if dato is None:

            resultado[nombre] = {
                "valor": None,
                "unidad": None,
                "timestamp": None,
                "timestamp_utc": None
            }

            continue

        resultado[nombre] = {

            "valor":
                dato["valor"],

            "unidad":
                dato["unidad"],

            "timestamp_utc":
                dato["timestamp_utc"],

            "timestamp":
                utc_a_colombia_iso(
                    dato["timestamp_utc"]
                )
        }

    return resultado


# =========================================================
# API - HISTÓRICO
# =========================================================

@app.get(
    "/api/historico"
)
async def api_historico(

    sensor: str = Query(...),

    variable: str = Query(...),

    desde: str = Query(...),

    hasta: str = Query(...)
):

    try:

        # -------------------------------------------------
        # Validar formato de fechas
        # -------------------------------------------------

        desde_dt = datetime.fromisoformat(
            desde
        )

        hasta_dt = datetime.fromisoformat(
            hasta
        )


        # -------------------------------------------------
        # Validar orden
        # -------------------------------------------------

        if hasta_dt <= desde_dt:

            raise HTTPException(
                status_code=400,
                detail=(
                    "La fecha final debe ser "
                    "mayor que la inicial."
                )
            )


        # -------------------------------------------------
        # Rango mínimo: 10 minutos
        # -------------------------------------------------

        diferencia_segundos = (
            hasta_dt -
            desde_dt
        ).total_seconds()

        if diferencia_segundos < 600:

            raise HTTPException(
                status_code=400,
                detail=(
                    "El rango mínimo es "
                    "de 10 minutos."
                )
            )


        # -------------------------------------------------
        # Convertir filtro Colombia -> UTC
        # -------------------------------------------------

        desde_utc = local_a_utc_iso(
            desde
        )

        hasta_utc = local_a_utc_iso(
            hasta
        )


        # -------------------------------------------------
        # Consultar SQLite
        # -------------------------------------------------

        datos = db_service.consultar_historico(
            sensor=sensor,
            variable=variable,
            desde_utc=desde_utc,
            hasta_utc=hasta_utc
        )


        # -------------------------------------------------
        # Agregar hora Colombia para la web
        # -------------------------------------------------

        datos_web = []

        for punto in datos:

            timestamp_utc = punto[
                "timestamp"
            ]

            datos_web.append({

                "timestamp_utc":
                    timestamp_utc,

                "timestamp":
                    utc_a_colombia_iso(
                        timestamp_utc
                    ),

                "valor":
                    punto["valor"],

                "unidad":
                    punto["unidad"]
            })


        return {

            "sensor":
                sensor,

            "variable":
                variable,

            "desde":
                desde,

            "hasta":
                hasta,

            "desde_utc":
                desde_utc,

            "hasta_utc":
                hasta_utc,

            "cantidad":
                len(datos_web),

            "datos":
                datos_web
        }


    except HTTPException:
        raise


    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Formato de fecha inválido. "
                "Use YYYY-MM-DDTHH:MM"
            )
        ) from e


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Error consultando histórico: "
                f"{type(e).__name__}: {e}"
            )
        ) from e
        
# =========================================================
# PROCESO
# =========================================================

@app.get(
    "/proceso",
    response_class=HTMLResponse
)
async def pagina_proceso(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="proceso.html",
        context={}
    )


@app.get(
    "/api/proceso/actual"
)
async def api_proceso_actual():

    proceso = db_service.obtener_proceso_activo()

    if proceso is None:

        return {
            "activo": False,
            "proceso": None
        }

    proceso["inicio"] = utc_a_colombia_iso(
        proceso["inicio_utc"]
    )

    return {
        "activo": True,
        "proceso": proceso
    }


@app.post(
    "/api/proceso/iniciar"
)
async def api_proceso_iniciar(
    lote: str = Form(""),
    observaciones: str = Form("")
):

    resultado = db_service.iniciar_proceso(
        lote=lote.strip() or None,
        observaciones=(
            observaciones.strip() or None
        )
    )

    if not resultado["ok"]:

        raise HTTPException(
            status_code=409,
            detail=resultado["mensaje"]
        )

    return resultado


@app.post(
    "/api/proceso/finalizar"
)
async def api_proceso_finalizar():

    resultado = db_service.finalizar_proceso()

    if not resultado["ok"]:

        raise HTTPException(
            status_code=409,
            detail=resultado["mensaje"]
        )

    return resultado

# =========================================================
# API - CICLOS CO2 DEL PROCESO
# =========================================================

@app.get(
    "/api/proceso/ciclos"
)
async def api_proceso_ciclos(
    modo: str = Query("activo")
):
    """
    Devuelve los ciclos CO2 del proceso activo o del último
    proceso histórico de prueba.

    modo=activo
    modo=historico
    """

    db_service.init_db()

    with sqlite3.connect(db_service.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if modo == "historico":
            proceso = conn.execute(
                """
                SELECT
                    id, inicio_utc, fin_utc, lote,
                    observaciones, estado
                FROM procesos
                WHERE lote = 'HIST-CO2-22SEP-PRUEBA'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        else:
            proceso = conn.execute(
                """
                SELECT
                    id, inicio_utc, fin_utc, lote,
                    observaciones, estado
                FROM procesos
                WHERE estado = 'ACTIVO'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if proceso is None:
            return {
                "ok": True,
                "modo": modo,
                "proceso": None,
                "resumen": {
                    "ciclos": 0,
                    "low_high_promedio_s": None,
                    "purga_promedio_s": None,
                    "intervalo_promedio_s": None,
                    "ultimo_intervalo_s": None
                },
                "ciclos": []
            }

        filas = conn.execute(
            """
            SELECT
                id,
                proceso_id,
                numero_ciclo,
                inicio_utc,
                fin_utc,
                purga_inicio_utc,
                purga_fin_utc,
                duracion_segundos,
                purga_duracion_segundos,
                intervalo_purgas_segundos,
                co2_purge_start_ppm,
                co2_purge_end_ppm,
                temperatura_media,
                humedad_media,
                c2h4_medio,
                estado
            FROM ciclos_co2
            WHERE proceso_id = ?
            ORDER BY COALESCE(numero_ciclo, id) ASC
            """,
            (proceso["id"],)
        ).fetchall()

    ciclos = []

    for fila in filas:
        item = dict(fila)

        for campo in (
            "inicio_utc",
            "fin_utc",
            "purga_inicio_utc",
            "purga_fin_utc"
        ):
            valor = item.get(campo)
            item[campo.replace("_utc", "")] = (
                utc_a_colombia_iso(valor)
                if valor
                else None
            )

        ciclos.append(item)

    cerrados = [
        c for c in ciclos
        if c.get("estado") == "CERRADO"
    ]

    def promedio(campo):
        valores = [
            float(c[campo])
            for c in cerrados
            if c.get(campo) is not None
        ]
        return (
            sum(valores) / len(valores)
            if valores
            else None
        )

    intervalos = [
        float(c["intervalo_purgas_segundos"])
        for c in cerrados
        if c.get("intervalo_purgas_segundos") is not None
    ]

    proceso_dict = dict(proceso)
    proceso_dict["inicio"] = (
        utc_a_colombia_iso(proceso_dict["inicio_utc"])
        if proceso_dict.get("inicio_utc")
        else None
    )
    proceso_dict["fin"] = (
        utc_a_colombia_iso(proceso_dict["fin_utc"])
        if proceso_dict.get("fin_utc")
        else None
    )

    return {
        "ok": True,
        "modo": modo,
        "proceso": proceso_dict,
        "resumen": {
            "ciclos": len(cerrados),
            "low_high_promedio_s": promedio("duracion_segundos"),
            "purga_promedio_s": promedio("purga_duracion_segundos"),
            "intervalo_promedio_s": (
                sum(intervalos) / len(intervalos)
                if intervalos
                else None
            ),
            "ultimo_intervalo_s": (
                intervalos[-1]
                if intervalos
                else None
            )
        },
        "ciclos": ciclos
    }
