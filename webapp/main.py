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

import os
import yaml
import tempfile
import socket
import shutil
import time
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
# =========================================================
# EVENTOS
# =========================================================

@app.get(
    "/eventos",
    response_class=HTMLResponse
)
async def pagina_eventos(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="eventos.html",
        context={}
    )


@app.get(
    "/api/eventos"
)
async def api_eventos(
    limite: int = Query(
        200,
        ge=1,
        le=1000
    ),
    tipo: str | None = Query(
        None
    ),
    desde: str | None = Query(
        None
    ),
    hasta: str | None = Query(
        None
    )
):

    desde_utc = None
    hasta_utc = None

    if desde:

        desde_utc = local_a_utc_iso(
            desde
        )

    if hasta:

        hasta_utc = local_a_utc_iso(
            hasta
        )

    eventos = db_service.obtener_eventos(
        limite=limite,
        tipo=tipo,
        desde_utc=desde_utc,
        hasta_utc=hasta_utc
    )

    resultado = []

    for evento in eventos:

        item = dict(
            evento
        )

        item["timestamp"] = (
            utc_a_colombia_iso(
                item["timestamp_utc"]
            )
        )

        resultado.append(
            item
        )

    return {
        "cantidad":
            len(resultado),

        "eventos":
            resultado
    }


@app.get(
    "/api/eventos/tipos"
)
async def api_eventos_tipos():

    tipos = (
        db_service.obtener_tipos_evento()
    )

    return {
        "tipos":
            tipos
    }
    
# =========================================================
# GUARDAR CONFIGURACIÓN HUMEDAD
# =========================================================

@app.post(
    "/api/configuracion/humedad"
)
async def api_guardar_configuracion_humedad(
    request: Request
):

    try:

        datos = await request.json()

        try:

            low = float(
                datos["low"]
            )

            high = float(
                datos["high"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ) as e:

            raise HTTPException(
                status_code=400,
                detail="Valores de humedad inválidos."
            ) from e


        # -------------------------------------------------
        # VALIDACIONES
        # -------------------------------------------------

        if (
            low < 0
            or
            high > 100
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "La humedad debe estar "
                    "entre 0 y 100 %."
                )
            )


        if low >= high:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Humedad LOW debe ser "
                    "menor que HIGH."
                )
            )


        # -------------------------------------------------
        # YAML
        # -------------------------------------------------

        ruta = (
            BASE_DIR.parent /
            "device" /
            "tht03r.yml"
        )


        if not ruta.exists():

            raise HTTPException(
                status_code=500,
                detail=(
                    f"No existe archivo THT03R: "
                    f"{ruta}"
                )
            )


        with open(
            ruta,
            "r",
            encoding="utf-8"
        ) as archivo:

            lineas = archivo.readlines()


        nuevas_lineas = []

        encontrado_low = False
        encontrado_high = False


        for linea in lineas:

            stripped = linea.lstrip()

            indentacion = (
                linea[
                    :len(linea) -
                    len(stripped)
                ]
            )


            if stripped.startswith(
                "hu_ppm_low:"
            ):

                comentario = ""

                if "#" in linea:

                    comentario = (
                        "  #" +
                        linea.split(
                            "#",
                            1
                        )[1].rstrip()
                    )

                nuevas_lineas.append(
                    f"{indentacion}"
                    f"hu_ppm_low: {low:g}"
                    f"{comentario}\n"
                )

                encontrado_low = True

                continue


            if stripped.startswith(
                "hu_ppm_high:"
            ):

                comentario = ""

                if "#" in linea:

                    comentario = (
                        "  #" +
                        linea.split(
                            "#",
                            1
                        )[1].rstrip()
                    )

                nuevas_lineas.append(
                    f"{indentacion}"
                    f"hu_ppm_high: {high:g}"
                    f"{comentario}\n"
                )

                encontrado_high = True

                continue


            nuevas_lineas.append(
                linea
            )


        if not (
            encontrado_low
            and
            encontrado_high
        ):

            raise HTTPException(
                status_code=500,
                detail=(
                    "No se encontraron "
                    "hu_ppm_low y hu_ppm_high "
                    "en tht03r.yml."
                )
            )


        # -------------------------------------------------
        # ESCRITURA ATÓMICA
        # -------------------------------------------------

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(
                ruta.parent
            ),
            delete=False
        ) as temporal:

            temporal.write(
                "".join(
                    nuevas_lineas
                )
            )

            ruta_temporal = Path(
                temporal.name
            )


        os.replace(
            ruta_temporal,
            ruta
        )


        # -------------------------------------------------
        # EVENTO
        # -------------------------------------------------

        db_service.guardar_evento(
            tipo="CONFIG_HUMEDAD",
            estado="ACTUALIZADA",
            valor=high,
            detalle=(
                f"LOW={low:g} % | "
                f"HIGH={high:g} %"
            )
        )


        return {
            "ok": True,
            "mensaje":
                "Configuración de humedad guardada.",
            "humedad": {
                "low": low,
                "high": high
            }
        }


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error guardando humedad: "
                f"{type(e).__name__}: {e}"
            )
        ) from e
    
# =========================================================
# CONFIGURACIÓN
# =========================================================

@app.get(
    "/configuracion",
    response_class=HTMLResponse
)
async def pagina_configuracion(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="configuracion.html",
        context={}
    )


@app.get(
    "/api/configuracion"
)
async def api_configuracion():

    try:

        # =====================================================
        # RUTAS DE CONFIGURACIÓN
        # =====================================================

        project_dir = BASE_DIR.parent

        ruta_co2 = Path(
            os.getenv(
                "CFG_CT01CO2",
                str(
                    project_dir /
                    "device" /
                    "ct01co2.yml"
                )
            )
        )

        ruta_humedad = Path(
            os.getenv(
                "CFG_THT03R",
                str(
                    project_dir /
                    "device" /
                    "tht03r.yml"
                )
            )
        )

        ruta_hvac = Path(
            os.getenv(
                "CFG_HVAC",
                str(
                    project_dir /
                    "device" /
                    "Samsung-HVAC.yml"
                )
            )
        )


        # =====================================================
        # CARGAR YAML
        # =====================================================

        def cargar_yaml(
            ruta
        ):

            if not ruta.exists():

                raise FileNotFoundError(
                    f"No existe archivo: {ruta}"
                )

            with open(
                ruta,
                "r",
                encoding="utf-8"
            ) as archivo:

                return (
                    yaml.safe_load(
                        archivo
                    )
                    or {}
                )


        cfg_co2 = cargar_yaml(
            ruta_co2
        )

        cfg_humedad = cargar_yaml(
            ruta_humedad
        )

        cfg_hvac = cargar_yaml(
            ruta_hvac
        )


        # =====================================================
        # CONFIGURACIÓN CO2
        # =====================================================

        co2 = (
            cfg_co2
            .get(
                "medidores",
                {}
            )
            .get(
                "ct01co2_sensor",
                {}
            )
        )

        control_co2 = (
            co2.get(
                "control",
                {}
            )
        )


        # =====================================================
        # CONFIGURACIÓN HUMEDAD / THT03R
        # =====================================================

        humedad = (
            cfg_humedad
            .get(
                "medidores",
                {}
            )
            .get(
                "tht03r_sensor",
                {}
            )
        )

        control_humedad = (
            humedad.get(
                "control",
                {}
            )
        )


        # =====================================================
        # CONFIGURACIÓN HVAC SAMSUNG
        # =====================================================

        hvac = (
            cfg_hvac
            .get(
                "medidores",
                {}
            )
            .get(
                "samsung_mim_b19n",
                {}
            )
        )

        control_hvac = (
            hvac.get(
                "control",
                {}
            )
        )


        # =====================================================
        # MODO HVAC
        # =====================================================

        modos_hvac = {
            0: "Auto",
            1: "Cool",
            2: "Dry",
            3: "Fan",
            4: "Heat"
        }

        velocidad_hvac = {
            0: "Auto",
            1: "Low",
            2: "Medium",
            3: "High"
        }

        mode = control_hvac.get(
            "mode"
        )

        fan_speed = control_hvac.get(
            "fan_speed"
        )


        # =====================================================
        # RESPUESTA
        # =====================================================

        return {

            "co2": {

                "device":
                    co2.get(
                        "device_name"
                    ),

                "slave_id":
                    co2.get(
                        "slave_id"
                    ),

                "baudrate":
                    co2.get(
                        "baudrate"
                    ),

                "low":
                    control_co2.get(
                        "co2_ppm_low"
                    ),

                "high":
                    control_co2.get(
                        "co2_ppm_high"
                    ),

                "aire_fresco_minutos":
                    control_co2.get(
                        "aire_fresco_minutos"
                    )
            },


            "humedad": {

                "device":
                    humedad.get(
                        "device_name"
                    ),

                "slave_id":
                    humedad.get(
                        "slave_id"
                    ),

                "baudrate":
                    humedad.get(
                        "baudrate"
                    ),

                "low":
                    control_humedad.get(
                        "hu_ppm_low"
                    ),

                "high":
                    control_humedad.get(
                        "hu_ppm_high"
                    )
            },


            "hvac": {

                "enabled":
                    control_hvac.get(
                        "enabled"
                    ),

                "reference_sensor":
                    control_hvac.get(
                        "reference_sensor"
                    ),

                "temp_target":
                    control_hvac.get(
                        "temp_target"
                    ),

                "temp_low":
                    control_hvac.get(
                        "temp_low"
                    ),

                "temp_high":
                    control_hvac.get(
                        "temp_high"
                    ),

                "setpoint_min":
                    control_hvac.get(
                        "setpoint_min"
                    ),

                "setpoint_max":
                    control_hvac.get(
                        "setpoint_max"
                    ),

                "setpoint_step":
                    control_hvac.get(
                        "setpoint_step"
                    ),

                "mode":
                    mode,

                "mode_text":
                    modos_hvac.get(
                        mode,
                        str(mode)
                    ),

                "fan_speed":
                    fan_speed,

                "fan_speed_text":
                    velocidad_hvac.get(
                        fan_speed,
                        str(fan_speed)
                    ),

                "slave_id":
                    hvac.get(
                        "slave_id"
                    ),

                "baudrate":
                    hvac.get(
                        "baudrate"
                    ),

                "port":
                    hvac.get(
                        "port"
                    )
            }
        }


    except FileNotFoundError as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error cargando configuración: "
                f"{type(e).__name__}: {e}"
            )
        ) from e
        
        
# =========================================================
# GUARDAR CONFIGURACIÓN HVAC
# =========================================================

@app.post(
    "/api/configuracion/hvac"
)
async def api_guardar_configuracion_hvac(
    request: Request
):

    try:

        datos = await request.json()

        # -------------------------------------------------
        # VALORES RECIBIDOS
        # -------------------------------------------------

        try:

            temp_target = float(
                datos["temp_target"]
            )

            temp_low = float(
                datos["temp_low"]
            )

            temp_high = float(
                datos["temp_high"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ) as e:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Temperaturas inválidas."
                )
            ) from e


        # -------------------------------------------------
        # RUTA YAML HVAC
        # -------------------------------------------------

        project_dir = (
            BASE_DIR.parent
        )

        ruta_hvac = (
            BASE_DIR.parent /
            "device" /
            "Samsung-HVAC.yml"
        )


        if not ruta_hvac.exists():

            raise HTTPException(
                status_code=500,
                detail=(
                    f"No existe archivo HVAC: "
                    f"{ruta_hvac}"
                )
            )


        # -------------------------------------------------
        # LEER CONFIGURACIÓN ACTUAL
        # -------------------------------------------------

        with open(
            ruta_hvac,
            "r",
            encoding="utf-8"
        ) as archivo:

            cfg = (
                yaml.safe_load(
                    archivo
                )
                or {}
            )


        hvac = (
            cfg
            .get(
                "medidores",
                {}
            )
            .get(
                "samsung_mim_b19n",
                {}
            )
        )

        control = (
            hvac.get(
                "control",
                {}
            )
        )


        setpoint_min = float(
            control.get(
                "setpoint_min",
                16.0
            )
        )

        setpoint_max = float(
            control.get(
                "setpoint_max",
                26.0
            )
        )


        # -------------------------------------------------
        # VALIDACIONES
        # -------------------------------------------------

        valores = [
            temp_target,
            temp_low,
            temp_high
        ]


        for valor in valores:

            if (
                valor < setpoint_min
                or
                valor > setpoint_max
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Temperatura fuera del "
                        f"rango permitido "
                        f"{setpoint_min} a "
                        f"{setpoint_max} °C."
                    )
                )


        if temp_low >= temp_high:

            raise HTTPException(
                status_code=400,
                detail=(
                    "La banda baja debe ser "
                    "menor que la banda alta."
                )
            )


        if not (
            temp_low
            <= temp_target
            <= temp_high
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "La temperatura objetivo "
                    "debe estar entre la banda "
                    "baja y la banda alta."
                )
            )


        # -------------------------------------------------
        # ACTUALIZAR SOLO LAS 3 LÍNEAS
        # PRESERVANDO EL RESTO DEL YAML
        # -------------------------------------------------

        with open(
            ruta_hvac,
            "r",
            encoding="utf-8"
        ) as archivo:

            lineas = (
                archivo.readlines()
            )


        encontrados = {
            "temp_target": False,
            "temp_low": False,
            "temp_high": False
        }


        nuevas_lineas = []


        for linea in lineas:

            stripped = (
                linea.lstrip()
            )

            indentacion = (
                linea[
                    :len(linea) -
                    len(stripped)
                ]
            )


            if stripped.startswith(
                "temp_target:"
            ):

                comentario = ""

                if "#" in linea:

                    comentario = (
                        "  #" +
                        linea.split(
                            "#",
                            1
                        )[1].rstrip()
                    )

                nuevas_lineas.append(
                    f"{indentacion}"
                    f"temp_target: "
                    f"{temp_target:g}"
                    f"{comentario}\n"
                )

                encontrados[
                    "temp_target"
                ] = True

                continue


            if stripped.startswith(
                "temp_low:"
            ):

                comentario = ""

                if "#" in linea:

                    comentario = (
                        "  #" +
                        linea.split(
                            "#",
                            1
                        )[1].rstrip()
                    )

                nuevas_lineas.append(
                    f"{indentacion}"
                    f"temp_low: "
                    f"{temp_low:g}"
                    f"{comentario}\n"
                )

                encontrados[
                    "temp_low"
                ] = True

                continue


            if stripped.startswith(
                "temp_high:"
            ):

                comentario = ""

                if "#" in linea:

                    comentario = (
                        "  #" +
                        linea.split(
                            "#",
                            1
                        )[1].rstrip()
                    )

                nuevas_lineas.append(
                    f"{indentacion}"
                    f"temp_high: "
                    f"{temp_high:g}"
                    f"{comentario}\n"
                )

                encontrados[
                    "temp_high"
                ] = True

                continue


            nuevas_lineas.append(
                linea
            )


        if not all(
            encontrados.values()
        ):

            raise HTTPException(
                status_code=500,
                detail=(
                    "No se encontraron todos "
                    "los parámetros HVAC en "
                    "el YAML."
                )
            )


        # -------------------------------------------------
        # ESCRITURA ATÓMICA
        # -------------------------------------------------

        contenido = "".join(
            nuevas_lineas
        )


        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(
                ruta_hvac.parent
            ),
            delete=False
        ) as temporal:

            temporal.write(
                contenido
            )

            ruta_temporal = Path(
                temporal.name
            )


        os.replace(
            ruta_temporal,
            ruta_hvac
        )


        # -------------------------------------------------
        # REGISTRAR EVENTO
        # -------------------------------------------------

        db_service.guardar_evento(
            tipo="CONFIG_HVAC",
            estado="ACTUALIZADA",
            valor=temp_target,
            detalle=(
                f"Objetivo={temp_target:g} °C | "
                f"LOW={temp_low:g} °C | "
                f"HIGH={temp_high:g} °C"
            )
        )


        return {
            "ok": True,
            "mensaje":
                "Configuración HVAC guardada.",
            "hvac": {
                "temp_target":
                    temp_target,

                "temp_low":
                    temp_low,

                "temp_high":
                    temp_high
            }
        }


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error guardando HVAC: "
                f"{type(e).__name__}: {e}"
            )
        ) from e
        
 # =========================================================
# GUARDAR CONFIGURACIÓN CO2
# =========================================================

@app.post(
    "/api/configuracion/co2"
)
async def api_guardar_configuracion_co2(
    request: Request
):

    try:

        datos = await request.json()

        low = int(
            datos["low"]
        )

        high = int(
            datos["high"]
        )

        aire_fresco = int(
            datos["aire_fresco_minutos"]
        )


        if low < 0:

            raise HTTPException(
                status_code=400,
                detail="CO2 LOW inválido."
            )


        if high <= low:

            raise HTTPException(
                status_code=400,
                detail=(
                    "CO2 HIGH debe ser "
                    "mayor que LOW."
                )
            )


        if aire_fresco <= 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "El tiempo de aire fresco "
                    "debe ser mayor que cero."
                )
            )


        ruta = (
            BASE_DIR.parent /
            "device" /
            "ct01co2.yml"
        )


        with open(
            ruta,
            "r",
            encoding="utf-8"
        ) as archivo:

            lineas = archivo.readlines()


        nuevas = []


        for linea in lineas:

            stripped = linea.lstrip()

            indentacion = (
                linea[
                    :len(linea) -
                    len(stripped)
                ]
            )


            if stripped.startswith(
                "co2_ppm_low:"
            ):

                nuevas.append(
                    f"{indentacion}"
                    f"co2_ppm_low: {low}\n"
                )

                continue


            if stripped.startswith(
                "co2_ppm_high:"
            ):

                nuevas.append(
                    f"{indentacion}"
                    f"co2_ppm_high: {high}\n"
                )

                continue


            if stripped.startswith(
                "aire_fresco_minutos:"
            ):

                nuevas.append(
                    f"{indentacion}"
                    f"aire_fresco_minutos: "
                    f"{aire_fresco}\n"
                )

                continue


            nuevas.append(
                linea
            )


        ruta.write_text(
            "".join(nuevas),
            encoding="utf-8"
        )


        db_service.guardar_evento(
            tipo="CONFIG_CO2",
            estado="ACTUALIZADA",
            valor=high,
            detalle=(
                f"LOW={low} ppm | "
                f"HIGH={high} ppm | "
                f"Aire fresco={aire_fresco} min"
            )
        )


        return {
            "ok": True
        }


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error guardando CO2: "
                f"{type(e).__name__}: {e}"
            )
        ) from e   
        
# =========================================================
# SISTEMA
# =========================================================

@app.get(
    "/sistema",
    response_class=HTMLResponse
)
async def pagina_sistema(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="sistema.html",
        context={}
    )


# =========================================================
# UTILIDADES SISTEMA
# =========================================================

def _leer_temperatura_cpu():

    try:

        ruta = Path(
            "/sys/class/thermal/"
            "thermal_zone0/temp"
        )

        if not ruta.exists():
            return None

        valor = float(
            ruta.read_text(
                encoding="utf-8"
            ).strip()
        )

        return round(
            valor / 1000.0,
            1
        )

    except Exception:
        return None


def _leer_cpu_stat():

    try:

        with open(
            "/proc/stat",
            "r",
            encoding="utf-8"
        ) as archivo:

            linea = archivo.readline()

        partes = linea.split()

        if not partes:
            return None

        valores = [
            int(valor)
            for valor in partes[1:]
        ]

        idle = (
            valores[3] +
            (
                valores[4]
                if len(valores) > 4
                else 0
            )
        )

        total = sum(
            valores
        )

        return {
            "idle": idle,
            "total": total
        }

    except Exception:
        return None


def _leer_uso_cpu():

    primero = _leer_cpu_stat()

    if primero is None:
        return None

    time.sleep(
        0.15
    )

    segundo = _leer_cpu_stat()

    if segundo is None:
        return None

    delta_total = (
        segundo["total"] -
        primero["total"]
    )

    delta_idle = (
        segundo["idle"] -
        primero["idle"]
    )

    if delta_total <= 0:
        return None

    uso = (
        100.0 *
        (
            1.0 -
            (
                delta_idle /
                delta_total
            )
        )
    )

    return round(
        uso,
        1
    )


def _leer_ram():

    try:

        datos = {}

        with open(
            "/proc/meminfo",
            "r",
            encoding="utf-8"
        ) as archivo:

            for linea in archivo:

                if ":" not in linea:
                    continue

                clave, valor = (
                    linea.split(
                        ":",
                        1
                    )
                )

                numero = (
                    valor
                    .strip()
                    .split()[0]
                )

                datos[
                    clave
                ] = int(
                    numero
                )

        total_kb = datos.get(
            "MemTotal"
        )

        disponible_kb = datos.get(
            "MemAvailable"
        )

        if (
            total_kb is None
            or
            disponible_kb is None
        ):
            return None

        usado_kb = (
            total_kb -
            disponible_kb
        )

        porcentaje = (
            usado_kb /
            total_kb *
            100.0
        )

        return {
            "total_mb":
                round(
                    total_kb / 1024.0,
                    1
                ),

            "usado_mb":
                round(
                    usado_kb / 1024.0,
                    1
                ),

            "porcentaje":
                round(
                    porcentaje,
                    1
                )
        }

    except Exception:
        return None


def _leer_disco():

    try:

        uso = shutil.disk_usage(
            "/"
        )

        porcentaje = (
            uso.used /
            uso.total *
            100.0
        )

        return {
            "total_gb":
                round(
                    uso.total /
                    (1024 ** 3),
                    1
                ),

            "usado_gb":
                round(
                    uso.used /
                    (1024 ** 3),
                    1
                ),

            "libre_gb":
                round(
                    uso.free /
                    (1024 ** 3),
                    1
                ),

            "porcentaje":
                round(
                    porcentaje,
                    1
                )
        }

    except Exception:
        return None


def _leer_uptime():

    try:

        with open(
            "/proc/uptime",
            "r",
            encoding="utf-8"
        ) as archivo:

            segundos = float(
                archivo
                .read()
                .split()[0]
            )

        dias = int(
            segundos // 86400
        )

        segundos = (
            segundos % 86400
        )

        horas = int(
            segundos // 3600
        )

        segundos = (
            segundos % 3600
        )

        minutos = int(
            segundos // 60
        )

        return {
            "dias": dias,
            "horas": horas,
            "minutos": minutos
        }

    except Exception:
        return None


def _obtener_ip_local():

    socket_udp = None

    try:

        socket_udp = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        socket_udp.connect(
            (
                "8.8.8.8",
                80
            )
        )

        return (
            socket_udp
            .getsockname()[0]
        )

    except Exception:

        try:

            return socket.gethostbyname(
                socket.gethostname()
            )

        except Exception:

            return None

    finally:

        if socket_udp is not None:

            socket_udp.close()


def _hay_internet():

    try:

        conexion = (
            socket.create_connection(
                (
                    "1.1.1.1",
                    53
                ),
                timeout=1.0
            )
        )

        conexion.close()

        return True

    except Exception:

        return False


@app.get(
    "/api/sistema"
)
async def api_sistema():

    try:

        # =================================================
        # RASPBERRY
        # =================================================

        temperatura_cpu = (
            _leer_temperatura_cpu()
        )

        uso_cpu = (
            _leer_uso_cpu()
        )

        ram = (
            _leer_ram()
        )

        disco = (
            _leer_disco()
        )

        uptime = (
            _leer_uptime()
        )


        # =================================================
        # RED
        # =================================================

        hostname = (
            socket.gethostname()
        )

        ip_local = (
            _obtener_ip_local()
        )

        internet = (
            _hay_internet()
        )


        # =================================================
        # BASE DE DATOS
        # =================================================

        db_service.init_db()

        with sqlite3.connect(
            db_service.DB_PATH
        ) as conn:

            mediciones = (
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM mediciones
                    """
                )
                .fetchone()[0]
            )

            eventos = (
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM eventos
                    """
                )
                .fetchone()[0]
            )

            ciclos = (
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM ciclos_co2
                    """
                )
                .fetchone()[0]
            )


        # =================================================
        # AWS QUEUE
        # =================================================

        pendientes = (
            db_service
            .aws_queue_contar_pendientes()
        )

        enviados = (
            db_service
            .aws_queue_contar_enviados()
        )


        # =================================================
        # PROCESO
        # =================================================

        proceso = (
            db_service
            .obtener_proceso_activo()
        )


        return {

            "raspberry": {

                "temperatura_cpu":
                    temperatura_cpu,

                "uso_cpu":
                    uso_cpu,

                "ram":
                    ram,

                "disco":
                    disco,

                "uptime":
                    uptime
            },


            "red": {

                "hostname":
                    hostname,

                "ip":
                    ip_local,

                "internet":
                    internet
            },


            "database": {

                "estado":
                    "OK",

                "mediciones":
                    int(
                        mediciones
                    ),

                "eventos":
                    int(
                        eventos
                    ),

                "ciclos":
                    int(
                        ciclos
                    )
            },


            "aws": {

                "pendientes":
                    pendientes,

                "enviados":
                    enviados
            },


            "proceso": {

                "activo":
                    proceso is not None,

                "id":
                    (
                        proceso.get(
                            "id"
                        )
                        if proceso
                        else None
                    )
            },


            "actualizacion":
                datetime.now(
                    TZ_LOCAL
                ).isoformat()
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error obteniendo estado "
                "del sistema: "
                f"{type(e).__name__}: {e}"
            )
        ) from e
# =========================================================
# HISTORIAL DE PROCESOS
# =========================================================

@app.get(
    "/api/procesos"
)
async def api_procesos(
    limite: int = Query(
        100,
        ge=1,
        le=500
    )
):

    db_service.init_db()

    with sqlite3.connect(
        db_service.DB_PATH
    ) as conn:

        conn.row_factory = sqlite3.Row

        filas = conn.execute(
            """
            SELECT
                p.id,
                p.inicio_utc,
                p.fin_utc,
                p.lote,
                p.observaciones,
                p.estado,

                COUNT(c.id) AS ciclos_total,

                SUM(
                    CASE
                        WHEN c.estado = 'CERRADO'
                        THEN 1
                        ELSE 0
                    END
                ) AS ciclos_cerrados

            FROM procesos p

            LEFT JOIN ciclos_co2 c
                ON c.proceso_id = p.id

            GROUP BY
                p.id,
                p.inicio_utc,
                p.fin_utc,
                p.lote,
                p.observaciones,
                p.estado

            ORDER BY p.id DESC

            LIMIT ?
            """,
            (
                limite,
            )
        ).fetchall()


    procesos = []


    for fila in filas:

        item = dict(
            fila
        )

        item["inicio"] = (
            utc_a_colombia_iso(
                item["inicio_utc"]
            )
            if item.get(
                "inicio_utc"
            )
            else None
        )

        item["fin"] = (
            utc_a_colombia_iso(
                item["fin_utc"]
            )
            if item.get(
                "fin_utc"
            )
            else None
        )


        duracion_segundos = None


        if (
            item.get(
                "inicio_utc"
            )
            and
            item.get(
                "fin_utc"
            )
        ):

            inicio_dt = datetime.fromisoformat(
                str(
                    item[
                        "inicio_utc"
                    ]
                ).replace(
                    "Z",
                    "+00:00"
                )
            )

            fin_dt = datetime.fromisoformat(
                str(
                    item[
                        "fin_utc"
                    ]
                ).replace(
                    "Z",
                    "+00:00"
                )
            )

            duracion_segundos = (
                fin_dt -
                inicio_dt
            ).total_seconds()


        item[
            "duracion_segundos"
        ] = (
            duracion_segundos
        )

        item[
            "ciclos_total"
        ] = int(
            item.get(
                "ciclos_total"
            )
            or 0
        )

        item[
            "ciclos_cerrados"
        ] = int(
            item.get(
                "ciclos_cerrados"
            )
            or 0
        )


        procesos.append(
            item
        )


    return {
        "cantidad":
            len(
                procesos
            ),

        "procesos":
            procesos
    }


# =========================================================
# DETALLE DE UN PROCESO
# =========================================================

@app.get(
    "/api/procesos/{proceso_id}/ciclos"
)
async def api_proceso_historico_ciclos(
    proceso_id: int
):

    db_service.init_db()

    with sqlite3.connect(
        db_service.DB_PATH
    ) as conn:

        conn.row_factory = sqlite3.Row


        proceso = conn.execute(
            """
            SELECT
                id,
                inicio_utc,
                fin_utc,
                lote,
                observaciones,
                estado
            FROM procesos
            WHERE id = ?
            LIMIT 1
            """,
            (
                proceso_id,
            )
        ).fetchone()


        if proceso is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Proceso no encontrado."
                )
            )


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

            ORDER BY
                COALESCE(
                    numero_ciclo,
                    id
                ) ASC
            """,
            (
                proceso_id,
            )
        ).fetchall()


    proceso_dict = dict(
        proceso
    )

    proceso_dict["inicio"] = (
        utc_a_colombia_iso(
            proceso_dict[
                "inicio_utc"
            ]
        )
        if proceso_dict.get(
            "inicio_utc"
        )
        else None
    )

    proceso_dict["fin"] = (
        utc_a_colombia_iso(
            proceso_dict[
                "fin_utc"
            ]
        )
        if proceso_dict.get(
            "fin_utc"
        )
        else None
    )


    ciclos = []


    for fila in filas:

        item = dict(
            fila
        )

        for campo in (
            "inicio_utc",
            "fin_utc",
            "purga_inicio_utc",
            "purga_fin_utc"
        ):

            valor = item.get(
                campo
            )

            item[
                campo.replace(
                    "_utc",
                    ""
                )
            ] = (
                utc_a_colombia_iso(
                    valor
                )
                if valor
                else None
            )

        ciclos.append(
            item
        )


    cerrados = [
        ciclo
        for ciclo in ciclos
        if ciclo.get(
            "estado"
        ) == "CERRADO"
    ]


    def promedio(
        campo
    ):

        valores = [
            float(
                ciclo[
                    campo
                ]
            )
            for ciclo in cerrados
            if ciclo.get(
                campo
            ) is not None
        ]

        return (
            sum(
                valores
            ) /
            len(
                valores
            )
            if valores
            else None
        )


    return {

        "ok": True,

        "proceso":
            proceso_dict,

        "resumen": {

            "ciclos":
                len(
                    cerrados
                ),

            "low_high_promedio_s":
                promedio(
                    "duracion_segundos"
                ),

            "purga_promedio_s":
                promedio(
                    "purga_duracion_segundos"
                ),

            "intervalo_promedio_s":
                promedio(
                    "intervalo_purgas_segundos"
                )
        },

        "ciclos":
            ciclos
    }