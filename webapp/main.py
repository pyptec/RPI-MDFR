from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.services import db_service


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
# ZONA HORARIA
# =========================================================

TZ_LOCAL = ZoneInfo(
    "America/Bogota"
)

TZ_UTC = ZoneInfo(
    "UTC"
)


# =========================================================
# UTILIDAD FECHAS
# =========================================================

def local_a_utc_iso(fecha_texto):
    """
    Entrada:
        2026-09-23T08:10

    Se interpreta como hora Colombia y se convierte a UTC.
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
    Convierte fecha almacenada en UTC
    a hora local Colombia.
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
# API HISTÓRICO
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
                "timestamp": None
            }

            continue

        resultado[nombre] = {
            "valor": dato["valor"],
            "unidad": dato["unidad"],
            "timestamp": utc_a_colombia_iso(
                dato["timestamp_utc"]
            )
        }

    return resultado