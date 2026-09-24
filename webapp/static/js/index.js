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
actualizarValores();


// Actualizar cada 10 segundos
setInterval(
    actualizarValores,
    10000
);