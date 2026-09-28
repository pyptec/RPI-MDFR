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

actualizarValores();
actualizarProcesoHome();

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