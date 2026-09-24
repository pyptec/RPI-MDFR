let inicioProcesoMs = null;
let modoCiclos = "historico";


function elemento(id) {
    return document.getElementById(id);
}


function formatoFecha(timestamp) {

    if (!timestamp) {
        return "--";
    }

    try {

        return new Date(timestamp).toLocaleString(
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

    } catch (error) {

        console.error(
            "Error formateando fecha:",
            error
        );

        return "--";
    }
}


function formatoDuracion(segundos) {

    if (
        segundos === null ||
        segundos === undefined ||
        segundos === "" ||
        isNaN(Number(segundos))
    ) {
        return "--";
    }

    let total = Math.max(
        0,
        Math.round(Number(segundos))
    );

    const dias =
        Math.floor(total / 86400);

    total %= 86400;

    const horas =
        Math.floor(total / 3600);

    total %= 3600;

    const minutos =
        Math.floor(total / 60);

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


function formatoPpm(valor) {

    if (
        valor === null ||
        valor === undefined ||
        isNaN(Number(valor))
    ) {
        return "--";
    }

    return (
        Math.round(Number(valor)) +
        " ppm"
    );
}


function actualizarCronometro() {

    const campo =
        elemento("tiempoActual");

    if (
        !campo ||
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

    campo.innerText =
        formatoDuracion(segundos);
}


async function cargarProceso() {

    try {

        const response =
            await fetch(
                "/api/proceso/actual",
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando proceso"
            );
        }


        const estado =
            elemento("estadoProceso");

        const btnIniciar =
            elemento("btnIniciar");

        const btnFinalizar =
            elemento("btnFinalizar");


        if (!data.activo) {

            if (estado) {

                estado.innerHTML =
                    "<strong>Sin proceso activo</strong>";
            }


            if (elemento("loteActual")) {
                elemento("loteActual").innerText =
                    "--";
            }


            if (elemento("inicioActual")) {
                elemento("inicioActual").innerText =
                    "--";
            }


            if (elemento("tiempoActual")) {
                elemento("tiempoActual").innerText =
                    "--";
            }


            if (elemento("observacionesActuales")) {

                elemento(
                    "observacionesActuales"
                ).innerText =
                    "--";
            }


            inicioProcesoMs = null;


            if (btnIniciar) {
                btnIniciar.disabled = false;
            }


            if (btnFinalizar) {
                btnFinalizar.disabled = true;
            }


            return;
        }


        const proceso =
            data.proceso;


        if (estado) {

            estado.innerHTML =
                "<strong>PROCESO ACTIVO</strong>";
        }


        if (elemento("loteActual")) {

            elemento(
                "loteActual"
            ).innerText =
                proceso.lote || "--";
        }


        if (elemento("inicioActual")) {

            elemento(
                "inicioActual"
            ).innerText =
                formatoFecha(
                    proceso.inicio
                );
        }


        if (
            elemento(
                "observacionesActuales"
            )
        ) {

            elemento(
                "observacionesActuales"
            ).innerText =
                proceso.observaciones ||
                "--";
        }


        inicioProcesoMs =
            new Date(
                proceso.inicio
            ).getTime();


        actualizarCronometro();


        if (btnIniciar) {
            btnIniciar.disabled = true;
        }


        if (btnFinalizar) {
            btnFinalizar.disabled = false;
        }


    } catch (error) {

        console.error(
            "Error cargarProceso:",
            error
        );


        if (
            elemento(
                "estadoProceso"
            )
        ) {

            elemento(
                "estadoProceso"
            ).innerText =
                "Error consultando proceso";
        }
    }
}


function actualizarBotonesModo() {

    const activo =
        elemento(
            "btnCiclosActivo"
        );

    const historico =
        elemento(
            "btnCiclosHistorico"
        );


    if (activo) {

        activo.disabled =
            modoCiclos === "activo";
    }


    if (historico) {

        historico.disabled =
            modoCiclos === "historico";
    }
}


function ponerTexto(
    id,
    valor
) {

    const campo =
        elemento(id);

    if (campo) {

        campo.innerText =
            valor;
    }
}


function pintarResumen(
    resumen
) {

    resumen =
        resumen || {};


    /*
     * IMPORTANTE:
     *
     * La API actual devuelve:
     *
     * resumen.ciclos
     *
     * NO:
     * resumen.ciclos_completos
     */

    ponerTexto(
        "kpiCiclos",
        resumen.ciclos !== undefined
            ? resumen.ciclos
            : 0
    );


    ponerTexto(
        "kpiLowHigh",
        formatoDuracion(
            resumen.low_high_promedio_s
        )
    );


    ponerTexto(
        "kpiPurga",
        formatoDuracion(
            resumen.purga_promedio_s
        )
    );


    ponerTexto(
        "kpiIntervalo",
        formatoDuracion(
            resumen.intervalo_promedio_s
        )
    );


    ponerTexto(
        "kpiUltimoIntervalo",
        formatoDuracion(
            resumen.ultimo_intervalo_s
        )
    );
}


function pintarOrigen(
    data
) {

    const campo =
        elemento(
            "origenCiclos"
        );


    if (!campo) {
        return;
    }


    if (!data.proceso) {

        if (
            modoCiclos ===
            "activo"
        ) {

            campo.innerText =
                "No existe un proceso activo.";

        } else {

            campo.innerText =
                "No existe histórico de prueba.";
        }

        return;
    }


    if (
        modoCiclos ===
        "historico"
    ) {

        campo.innerText =
            "Histórico reconstruido de prueba" +
            " | Proceso ID " +
            data.proceso.id +
            " | Lote " +
            (
                data.proceso.lote ||
                "--"
            );

    } else {

        campo.innerText =
            "Proceso activo" +
            " | Proceso ID " +
            data.proceso.id +
            " | Lote " +
            (
                data.proceso.lote ||
                "--"
            );
    }
}


function pintarTabla(
    ciclos
) {

    const tbody =
        elemento(
            "tablaCiclos"
        );


    if (!tbody) {

        console.error(
            "No existe tablaCiclos en proceso.html"
        );

        return;
    }


    if (
        !Array.isArray(ciclos) ||
        ciclos.length === 0
    ) {

        tbody.innerHTML =
            `
            <tr>
                <td colspan="10">
                    No hay ciclos registrados.
                </td>
            </tr>
            `;

        return;
    }


    let html = "";


    for (
        const ciclo
        of ciclos
    ) {

        const numero =
            ciclo.numero_ciclo !== null &&
            ciclo.numero_ciclo !== undefined

                ? ciclo.numero_ciclo

                : ciclo.id;


        html +=
            `
            <tr>

                <td>
                    ${numero}
                </td>

                <td>
                    ${formatoFecha(
                        ciclo.inicio
                    )}
                </td>

                <td>
                    ${formatoFecha(
                        ciclo.purga_inicio
                    )}
                </td>

                <td>
                    ${formatoFecha(
                        ciclo.purga_fin
                    )}
                </td>

                <td>
                    ${formatoDuracion(
                        ciclo.duracion_segundos
                    )}
                </td>

                <td>
                    ${formatoDuracion(
                        ciclo.purga_duracion_segundos
                    )}
                </td>

                <td>
                    ${formatoDuracion(
                        ciclo.intervalo_purgas_segundos
                    )}
                </td>

                <td>
                    ${formatoPpm(
                        ciclo.co2_purge_start_ppm
                    )}
                </td>

                <td>
                    ${formatoPpm(
                        ciclo.co2_purge_end_ppm
                    )}
                </td>

                <td>
                    ${ciclo.estado || "--"}
                </td>

            </tr>
            `;
    }


    tbody.innerHTML =
        html;
}


async function cargarCiclos() {

    try {

        actualizarBotonesModo();


        ponerTexto(
            "origenCiclos",
            "Consultando ciclos..."
        );


        const url =
            "/api/proceso/ciclos?modo=" +
            encodeURIComponent(
                modoCiclos
            );


        console.log(
            "Consultando:",
            url
        );


        const response =
            await fetch(
                url,
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        console.log(
            "Respuesta ciclos:",
            data
        );


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando ciclos"
            );
        }


        pintarResumen(
            data.resumen
        );


        pintarOrigen(
            data
        );


        pintarTabla(
            data.ciclos
        );


    } catch (error) {

        console.error(
            "Error cargarCiclos:",
            error
        );


        ponerTexto(
            "origenCiclos",
            "Error consultando ciclos: " +
            error.message
        );


        const tbody =
            elemento(
                "tablaCiclos"
            );


        if (tbody) {

            tbody.innerHTML =
                `
                <tr>
                    <td colspan="10">
                        Error consultando ciclos.
                    </td>
                </tr>
                `;
        }
    }
}


async function cambiarModoCiclos(
    modo
) {

    modoCiclos =
        modo;

    await cargarCiclos();
}


async function iniciarProceso() {

    try {

        const lote =
            elemento(
                "lote"
            ).value;

        const observaciones =
            elemento(
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

            ponerTexto(
                "mensajeProceso",
                data.detail ||
                "Error"
            );

            return;
        }


        ponerTexto(
            "mensajeProceso",
            "Proceso iniciado correctamente."
        );


        await cargarProceso();


        if (
            modoCiclos ===
            "activo"
        ) {

            await cargarCiclos();
        }


    } catch (error) {

        console.error(
            "Error iniciarProceso:",
            error
        );
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


    try {

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

            ponerTexto(
                "mensajeProceso",
                data.detail ||
                "Error"
            );

            return;
        }


        ponerTexto(
            "mensajeProceso",
            "Proceso finalizado."
        );


        await cargarProceso();


        if (
            modoCiclos ===
            "activo"
        ) {

            await cargarCiclos();
        }


    } catch (error) {

        console.error(
            "Error finalizarProceso:",
            error
        );
    }
}


// =========================================================
// INICIO DE LA PÁGINA
// =========================================================

console.log(
    "proceso.js MDFR cargado"
);


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