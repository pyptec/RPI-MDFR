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
    "/api/historico"
)
async def api_historico(

    sensor: str = Query(...),

    variable: str = Query(...),

    desde: str = Query(...),

    hasta: str = Query(...)
):

    try:

        desde_dt = datetime.fromisoformat(
            desde
        )

        hasta_dt = datetime.fromisoformat(
            hasta
        )

        diferencia = (
            hasta_dt - desde_dt
        ).total_seconds()

        # Rango mínimo permitido: 10 minutos
        if diferencia < 600:

            raise HTTPException(
                status_code=400,
                detail="El rango mínimo es de 10 minutos."
            )

        if hasta_dt <= desde_dt:

            raise HTTPException(
                status_code=400,
                detail="La fecha final debe ser mayor que la inicial."
            )

        desde_utc = local_a_utc_iso(
            desde
        )

        hasta_utc = local_a_utc_iso(
            hasta
        )

        datos = db_service.consultar_historico(
            sensor=sensor,
            variable=variable,
            desde_utc=desde_utc,
            hasta_utc=hasta_utc
        )

        for punto in datos:

            punto["timestamp_utc"] = punto["timestamp"]

            punto["timestamp"] = utc_a_colombia_iso(
                punto["timestamp"]
            )
        return {
            "sensor": sensor,
            "variable": variable,
            "desde": desde,
            "hasta": hasta,
            "cantidad": len(datos),
            "datos": datos
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )