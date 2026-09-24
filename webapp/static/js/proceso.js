let inicioProcesoMs = null;
let modoCiclos = "historico";


function formatoFecha(timestamp) {

    if (!timestamp) {
        return "--";
    }

    return new Date(
        timestamp
    ).toLocaleString(
        "es-CO",
        {
            timeZone: "America/Bogota",
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        }
    );
}


function formatoDuracion(segundos) {

    if (
        segundos === null ||
        segundos === undefined ||
        Number.isNaN(Number(segundos))
    ) {
        return "--";
    }

    segundos = Math.max(
        0,
        Math.round(Number(segundos))
    );

    const dias =
        Math.floor(
            segundos / 86400
        );

    segundos %= 86400;

    const horas =
        Math.floor(
            segundos / 3600
        );

    segundos %= 3600;

    const minutos =
        Math.floor(
            segundos / 60
        );

    const seg =
        segundos % 60;

    if (dias > 0) {
        return (
            `${dias} d ` +
            `${String(horas).padStart(2, "0")}:` +
            `${String(minutos).padStart(2, "0")}:` +
            `${String(seg).padStart(2, "0")}`
        );
    }

    return (
        `${String(horas).padStart(2, "0")}:` +
        `${String(minutos).padStart(2, "0")}:` +
        `${String(seg).padStart(2, "0")}`
    );
}


function actualizarCronometro() {

    const elemento =
        document.getElementById(
            "tiempoActual"
        );

    if (
        !elemento ||
        inicioProcesoMs === null
    ) {
        return;
    }

    const ahora =
        Date.now();

    const segundos =
        (
            ahora -
            inicioProcesoMs
        ) / 1000;

    elemento.innerText =
        formatoDuracion(segundos);
}


async function cargarProceso() {

    try {

        const response =
            await fetch(
                "/api/proceso/actual"
            );

        const data =
            await response.json();

        const estado =
            document.getElementById(
                "estadoProceso"
            );

        const btnIniciar =
            document.getElementById(
                "btnIniciar"
            );

        const btnFinalizar =
            document.getElementById(
                "btnFinalizar"
            );


        if (!data.activo) {

            estado.innerHTML =
                "<strong>Sin proceso activo</strong>";

            document.getElementById(
                "loteActual"
            ).innerText = "--";

            document.getElementById(
                "inicioActual"
            ).innerText = "--";

            document.getElementById(
                "tiempoActual"
            ).innerText = "--";

            document.getElementById(
                "observacionesActuales"
            ).innerText = "--";

            inicioProcesoMs = null;

            btnIniciar.disabled = false;
            btnFinalizar.disabled = true;

            return;
        }


        const proceso =
            data.proceso;

        estado.innerHTML =
            "<strong>PROCESO ACTIVO</strong>";

        document.getElementById(
            "loteActual"
        ).innerText =
            proceso.lote || "--";

        document.getElementById(
            "inicioActual"
        ).innerText =
            formatoFecha(
                proceso.inicio
            );

        document.getElementById(
            "observacionesActuales"
        ).innerText =
            proceso.observaciones || "--";

        inicioProcesoMs =
            new Date(
                proceso.inicio
            ).getTime();

        actualizarCronometro();

        btnIniciar.disabled = true;
        btnFinalizar.disabled = false;

    } catch (error) {

        console.error(error);

        document.getElementById(
            "estadoProceso"
        ).innerText =
            "Error consultando proceso";
    }
}


function actualizarBotonesModo() {

    const activo =
        document.getElementById(
            "btnCiclosActivo"
        );

    const historico =
        document.getElementById(
            "btnCiclosHistorico"
        );

    if (!activo || !historico) {
        return;
    }

    activo.disabled =
        modoCiclos === "activo";

    historico.disabled =
        modoCiclos === "historico";
}


function valorPpm(valor) {

    if (
        valor === null ||
        valor === undefined
    ) {
        return "--";
    }

    return (
        `${Math.round(Number(valor))} ppm`
    );
}


function pintarCiclos(data) {

    const resumen =
        data.resumen || {};

    document.getElementById(
        "kpiCiclos"
    ).innerText =
        resumen.ciclos_completos ?? 0;

    document.getElementById(
        "kpiLowHigh"
    ).innerText =
        formatoDuracion(
            resumen.low_high_promedio_s
        );

    document.getElementById(
        "kpiPurga"
    ).innerText =
        formatoDuracion(
            resumen.purga_promedio_s
        );

    document.getElementById(
        "kpiIntervalo"
    ).innerText =
        formatoDuracion(
            resumen.intervalo_promedio_s
        );

    document.getElementById(
        "kpiUltimoIntervalo"
    ).innerText =
        formatoDuracion(
            resumen.ultimo_intervalo_s
        );


    const origen =
        document.getElementById(
            "origenCiclos"
        );

    if (!data.proceso) {

        origen.innerText =
            modoCiclos === "activo"
                ? "No existe un proceso activo."
                : "No existe histórico de prueba.";

    } else {

        const etiqueta =
            modoCiclos === "activo"
                ? "Proceso activo"
                : "Histórico reconstruido de prueba";

        origen.innerText =
            `${etiqueta} | ` +
            `Proceso ID ${data.proceso.id} | ` +
            `Lote ${data.proceso.lote || "--"}`;
    }


    const tbody =
        document.getElementById(
            "tablaCiclos"
        );

    const ciclos =
        data.ciclos || [];


    if (ciclos.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="10">
                    No hay ciclos registrados.
                </td>
            </tr>
        `;

        return;
    }


    tbody.innerHTML =
        ciclos.map(
            ciclo => `
                <tr>
                    <td>
                        ${ciclo.numero_ciclo ?? ciclo.id ?? "--"}
                    </td>

                    <td>
                        ${formatoFecha(ciclo.inicio)}
                    </td>

                    <td>
                        ${formatoFecha(ciclo.purga_inicio)}
                    </td>

                    <td>
                        ${formatoFecha(ciclo.purga_fin)}
                    </td>

                    <td>
                        ${formatoDuracion(ciclo.duracion_segundos)}
                    </td>

                    <td>
                        ${formatoDuracion(ciclo.purga_duracion_segundos)}
                    </td>

                    <td>
                        ${formatoDuracion(ciclo.intervalo_purgas_segundos)}
                    </td>

                    <td>
                        ${valorPpm(ciclo.co2_purge_start_ppm)}
                    </td>

                    <td>
                        ${valorPpm(ciclo.co2_purge_end_ppm)}
                    </td>

                    <td>
                        ${ciclo.estado || "--"}
                    </td>
                </tr>
            `
        ).join("");
}


async function cargarCiclos() {

    try {

        actualizarBotonesModo();

        const response =
            await fetch(
                `/api/proceso/ciclos?modo=${encodeURIComponent(modoCiclos)}`
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Error consultando ciclos"
            );
        }

        pintarCiclos(data);

    } catch (error) {

        console.error(error);

        document.getElementById(
            "origenCiclos"
        ).innerText =
            "Error consultando ciclos.";

        document.getElementById(
            "tablaCiclos"
        ).innerHTML = `
            <tr>
                <td colspan="10">
                    Error consultando ciclos.
                </td>
            </tr>
        `;
    }
}


async function cambiarModoCiclos(modo) {

    modoCiclos = modo;

    await cargarCiclos();
}


async function iniciarProceso() {

    const lote =
        document.getElementById(
            "lote"
        ).value;

    const observaciones =
        document.getElementById(
            "observaciones"
        ).value;

    const form =
        new FormData();

    form.append(
        "lote",
        lote
    );

    form.append(
        "observaciones",
        observaciones
    );


    const response =
        await fetch(
            "/api/proceso/iniciar",
            {
                method: "POST",
                body: form
            }
        );


    const data =
        await response.json();

    if (!response.ok) {

        document.getElementById(
            "mensajeProceso"
        ).innerText =
            data.detail || "Error";

        return;
    }


    document.getElementById(
        "mensajeProceso"
    ).innerText =
        "Proceso iniciado correctamente.";

    await cargarProceso();

    if (modoCiclos === "activo") {
        await cargarCiclos();
    }
}


async function finalizarProceso() {

    const confirmar =
        window.confirm(
            "¿Desea finalizar el proceso de maduración actual?"
        );

    if (!confirmar) {
        return;
    }


    const response =
        await fetch(
            "/api/proceso/finalizar",
            {
                method: "POST"
            }
        );


    const data =
        await response.json();

    if (!response.ok) {

        document.getElementById(
            "mensajeProceso"
        ).innerText =
            data.detail || "Error";

        return;
    }


    document.getElementById(
        "mensajeProceso"
    ).innerText =
        "Proceso finalizado.";

    await cargarProceso();

    if (modoCiclos === "activo") {
        await cargarCiclos();
    }
}


cargarProceso();
cargarCiclos();


setInterval(
    actualizarCronometro,
    1000
);


setInterval(
    cargarCiclos,
    30000
);