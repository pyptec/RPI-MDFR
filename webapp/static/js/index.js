function mostrarValor(
    id,
    dato,
    unidadEsperada
) {

    const elemento =
        document.getElementById(id);

    if (!elemento) {
        return;
    }

    if (
        !dato ||
        dato.valor === null ||
        dato.valor === undefined
    ) {

        elemento.innerText =
            "Sin datos";

        return;
    }

    let valor =
        Number(dato.valor);

    if (!Number.isFinite(valor)) {

        elemento.innerText =
            "Sin datos";

        return;
    }

    let textoValor;

    if (
        unidadEsperada === "ppm"
    ) {

        textoValor =
            valor.toFixed(0);

    } else {

        textoValor =
            valor.toFixed(1);
    }

    elemento.innerText =
        `${textoValor} ${unidadEsperada}`;
}


function formatoFecha(timestamp) {

    if (!timestamp) {
        return "--";
    }

    const fecha =
        new Date(timestamp);

    return fecha.toLocaleString(
        "es-CO",
        {
            timeZone:
                "America/Bogota",

            day:
                "2-digit",

            month:
                "2-digit",

            year:
                "numeric",

            hour:
                "2-digit",

            minute:
                "2-digit",

            second:
                "2-digit",

            hour12:
                false
        }
    );
}


async function actualizarValores() {

    try {

        const response =
            await fetch(
                "/api/actual"
            );

        if (!response.ok) {

            console.error(
                "Error API actual:",
                response.status
            );

            return;
        }

        const data =
            await response.json();


        mostrarValor(
            "valorTemperatura",
            data.temperatura,
            "°C"
        );


        mostrarValor(
            "valorHumedad",
            data.humedad,
            "%"
        );


        mostrarValor(
            "valorCO2",
            data.co2,
            "ppm"
        );


        mostrarValor(
            "valorC2H4",
            data.c2h4,
            "ppm"
        );


        mostrarValor(
            "valorPT100",
            data.pt100,
            "°C"
        );


        mostrarValor(
            "valorPT1000",
            data.pt1000,
            "°C"
        );


        let ultimaFecha = null;

        Object.values(
            data
        ).forEach(
            dato => {

                if (
                    dato &&
                    dato.timestamp
                ) {

                    const fecha =
                        new Date(
                            dato.timestamp
                        );

                    if (
                        !ultimaFecha ||
                        fecha >
                        ultimaFecha
                    ) {

                        ultimaFecha =
                            fecha;
                    }
                }
            }
        );


        const elemento =
            document.getElementById(
                "ultimaActualizacion"
            );

        if (elemento) {

            if (ultimaFecha) {

                elemento.innerText =
                    formatoFecha(
                        ultimaFecha.toISOString()
                    );

            } else {

                elemento.innerText =
                    "Sin datos";
            }
        }

    } catch (error) {

        console.error(
            "Error actualizando valores:",
            error
        );
    }
}


// Primera carga
//actualizarValores();

let inicioProcesoHomeMs = null;


function formatoDuracionHome(segundos) {

    if (
        segundos === null ||
        segundos === undefined ||
        isNaN(Number(segundos))
    ) {
        return "--";
    }

    let total =
        Math.max(
            0,
            Math.floor(
                Number(segundos)
            )
        );

    const dias =
        Math.floor(
            total / 86400
        );

    total %= 86400;

    const horas =
        Math.floor(
            total / 3600
        );

    total %= 3600;

    const minutos =
        Math.floor(
            total / 60
        );

    const segundosRestantes =
        total % 60;

    if (dias > 0) {

        return (
            dias +
            " d " +
            String(horas).padStart(2, "0") +
            ":" +
            String(minutos).padStart(2, "0") +
            ":" +
            String(segundosRestantes).padStart(2, "0")
        );
    }

    return (
        String(horas).padStart(2, "0") +
        ":" +
        String(minutos).padStart(2, "0") +
        ":" +
        String(segundosRestantes).padStart(2, "0")
    );
}


function actualizarTiempoProcesoHome() {

    const elemento =
        document.getElementById(
            "tiempoProceso"
        );

    if (!elemento) {
        return;
    }

    if (inicioProcesoHomeMs === null) {

        elemento.innerText = "--";

        return;
    }

    const segundos =
        (
            Date.now() -
            inicioProcesoHomeMs
        ) / 1000;

    elemento.innerText =
        formatoDuracionHome(
            segundos
        );
}


async function actualizarProcesoHome() {

    try {

        const responseProceso =
            await fetch(
                "/api/proceso/actual",
                {
                    cache: "no-store"
                }
            );

        const dataProceso =
            await responseProceso.json();

        if (!responseProceso.ok) {

            throw new Error(
                dataProceso.detail ||
                "Error consultando proceso"
            );
        }


        const estado =
            document.getElementById(
                "estadoProceso"
            );

        if (
            !dataProceso.activo ||
            !dataProceso.proceso
        ) {

            if (estado) {

                estado.innerText =
                    "SIN PROCESO";

                estado.className =
                    "estado-inactivo";
            }

        } else {

            if (estado) {

                estado.innerText =
                    "ACTIVO";

                estado.className =
                    "estado-activo";
            }
        }

        const inicio =
            document.getElementById(
                "inicioProceso"
            );


        if (
            !dataProceso.activo ||
            !dataProceso.proceso
        ) {

            if (estado) {
                estado.innerText =
                    "SIN PROCESO";
            }

            if (inicio) {
                inicio.innerText =
                    "--";
            }

            inicioProcesoHomeMs = null;

        } else {

            const proceso =
                dataProceso.proceso;

            if (estado) {
                estado.innerText =
                    "ACTIVO";
            }

            if (inicio) {

                inicio.innerText =
                    formatoFecha(
                        proceso.inicio
                    );
            }

            inicioProcesoHomeMs =
                new Date(
                    proceso.inicio
                ).getTime();
        }


        actualizarTiempoProcesoHome();


        const responseCiclos =
            await fetch(
                "/api/proceso/ciclos?modo=activo",
                {
                    cache: "no-store"
                }
            );

        const dataCiclos =
            await responseCiclos.json();

        if (!responseCiclos.ok) {

            throw new Error(
                dataCiclos.detail ||
                "Error consultando ciclos"
            );
        }


        const ciclos =
            document.getElementById(
                "ciclosCO2"
            );

        const ultimo =
            document.getElementById(
                "ultimoCicloCO2"
            );


        if (ciclos) {

            ciclos.innerText =
                dataCiclos.resumen &&
                dataCiclos.resumen.ciclos !== undefined

                    ? dataCiclos.resumen.ciclos

                    : 0;
        }


        if (ultimo) {

            const valor =
                dataCiclos.resumen
                    ? dataCiclos.resumen
                        .low_high_promedio_s
                    : null;

            ultimo.innerText =
                formatoDuracionHome(
                    valor
                );
        }

    } catch (error) {

        console.error(
            "Error actualizando proceso home:",
            error
        );
    }
}

function formatoEdadDato(
    segundos
) {

    if (
        segundos === null ||
        segundos === undefined
    ) {
        return "--";
    }


    segundos =
        Number(
            segundos
        );


    if (segundos < 60) {

        return (
            `${Math.round(segundos)} s`
        );
    }


    const minutos =
        segundos / 60;


    if (minutos < 60) {

        return (
            `${Math.round(minutos)} min`
        );
    }


    const horas =
        minutos / 60;


    return (
        `${horas.toFixed(1)} h`
    );
}


function pintarCalidadDato(
    id,
    dato
) {

    const elemento =
        document.getElementById(
            id
        );


    if (!elemento) {
        return;
    }


    if (!dato) {

        elemento.innerText =
            "SIN DATOS";

        elemento.className =
            "config-value estado-alerta";

        return;
    }


    const edad =
        formatoEdadDato(
            dato.edad_segundos
        );


    if (
        dato.estado === "OK"
    ) {

        elemento.innerText =
            `OK · hace ${edad}`;

        elemento.className =
            "config-value estado-activo";

    } else if (
        dato.estado === "ATRASADO"
    ) {

        elemento.innerText =
            `ATRASADO · hace ${edad}`;

        elemento.className =
            "config-value estado-alerta";

    } else {

        elemento.innerText =
            `SIN DATOS · hace ${edad}`;

        elemento.className =
            "config-value estado-alerta";
    }
}


async function actualizarEstadoOperacion() {

    try {

        const response =
            await fetch(
                "/api/estado-operacion",
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando estado operativo"
            );
        }


        // =============================================
        // PUERTA
        // =============================================

        const puerta =
            document.getElementById(
                "estadoPuerta"
            );


        if (puerta) {

            const estado =
                data.seguridad
                    ?.puerta
                    ?.estado ||
                "SIN DATOS";


            puerta.innerText =
                estado;


            puerta.className =
                (
                    estado === "CERRADA"
                )
                    ?
                    "config-value estado-activo"
                    :
                    "config-value estado-alerta";
        }


        // =============================================
        // HOMBRE ATRAPADO
        // =============================================

        const man =
            document.getElementById(
                "estadoMan"
            );


        if (man) {

            const activo =
                data.seguridad
                    ?.hombre_atrapado
                    ?.activo === true;


            man.innerText =
                activo
                    ?
                    "ACTIVO"
                    :
                    "NORMAL";


            man.className =
                activo
                    ?
                    "config-value estado-alerta"
                    :
                    "config-value estado-activo";
        }


        // =============================================
        // CALIDAD DE DATOS
        // =============================================

        pintarCalidadDato(
            "calidadCO2",
            data.datos?.co2
        );


        pintarCalidadDato(
            "calidadTemperatura",
            data.datos?.temperatura
        );


        pintarCalidadDato(
            "calidadHumedad",
            data.datos?.humedad
        );


        pintarCalidadDato(
            "calidadC2H4",
            data.datos?.c2h4
        );


        pintarCalidadDato(
            "calidadPT1000",
            data.datos?.pt1000
        );


    } catch (error) {

        console.error(
            "Error actualizarEstadoOperacion:",
            error
        );
    }
}
async function actualizarSaludSistema() {

    try {

        const response =
            await fetch(
                "/api/sistema",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando sistema"
            );
        }


        // =============================================
        // INTERNET
        // =============================================

        const internet =
            document.getElementById(
                "saludInternet"
            );


        if (internet) {

            if (
                data.red?.internet
            ) {

                internet.innerText =
                    "CONECTADO";

                internet.className =
                    "config-value estado-activo";

            } else {

                internet.innerText =
                    "SIN INTERNET";

                internet.className =
                    "config-value estado-alerta";
            }
        }


        // =============================================
        // AWS
        // =============================================

        const aws =
            document.getElementById(
                "saludAWS"
            );


        if (aws) {

            const pendientes =
                Number(
                    data.aws?.pendientes ?? 0
                );


            aws.innerText =
                pendientes;


            aws.className =
                (
                    pendientes === 0
                )
                    ?
                    "config-value estado-activo"
                    :
                    "config-value estado-alerta";
        }


        // =============================================
        // SQLITE
        // =============================================

        const db =
            document.getElementById(
                "saludDB"
            );


        if (db) {

            const estado =
                data.database?.estado ||
                "--";


            db.innerText =
                estado;


            db.className =
                (
                    estado === "OK"
                )
                    ?
                    "config-value estado-activo"
                    :
                    "config-value estado-alerta";
        }


        // =============================================
        // CPU
        // =============================================

        const cpu =
            document.getElementById(
                "saludCPU"
            );


        if (cpu) {

            const temp =
                data.raspberry
                    ?.temperatura_cpu;


            if (
                temp === null ||
                temp === undefined
            ) {

                cpu.innerText =
                    "--";

            } else {

                cpu.innerText =
                    `${temp} °C`;


                cpu.className =
                    (
                        temp < 70
                    )
                        ?
                        "config-value estado-activo"
                        :
                        "config-value estado-alerta";
            }
        }


    } catch (error) {

        console.error(
            "Error actualizarSaludSistema:",
            error
        );
    }
}
actualizarValores();
actualizarProcesoHome();
actualizarEstadoOperacion();


setInterval(
    actualizarEstadoOperacion,
    10000
);

setInterval(
    actualizarValores,
    10000
);

setInterval(
    actualizarProcesoHome,
    10000
);

setInterval(
    actualizarTiempoProcesoHome,
    1000
);