let inicioProcesoMs = null;

let modoCiclos = "activo";

let procesoHistoricoSeleccionado = null;


// =========================================================
// UTILIDADES
// =========================================================

function elemento(id) {

    return document.getElementById(id);
}


function ponerTexto(id, valor) {

    const campo = elemento(id);

    if (campo) {
        campo.innerText = valor;
    }
}


function escaparHtml(valor) {

    if (
        valor === null ||
        valor === undefined
    ) {
        return "";
    }

    return String(valor)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// =========================================================
// FORMATO FECHA
// =========================================================

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


// =========================================================
// FORMATO DURACIÓN
// =========================================================

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

    const reloj =
        String(horas).padStart(2, "0")
        +
        ":"
        +
        String(minutos).padStart(2, "0")
        +
        ":"
        +
        String(segundosRestantes).padStart(2, "0");

    if (dias > 0) {

        return (
            dias +
            " d " +
            reloj
        );
    }

    return reloj;
}


// =========================================================
// FORMATO PPM
// =========================================================

function formatoPpm(valor) {

    if (
        valor === null ||
        valor === undefined ||
        isNaN(Number(valor))
    ) {
        return "--";
    }

    return (
        Math.round(Number(valor))
        +
        " ppm"
    );
}


// =========================================================
// CRONÓMETRO PROCESO ACTIVO
// =========================================================

function actualizarCronometro() {

    const campo =
        elemento("tiempoActual");

    if (
        !campo ||
        inicioProcesoMs === null
    ) {
        return;
    }

    const segundos =
        (
            Date.now() -
            inicioProcesoMs
        ) / 1000;

    campo.innerText =
        formatoDuracion(segundos);
}


// =========================================================
// CARGAR PROCESO ACTUAL
// =========================================================

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


        // =================================================
        // SIN PROCESO
        // =================================================

        if (!data.activo) {

            if (estado) {

                estado.innerHTML =
                    "<strong>Sin proceso activo</strong>";
            }

            ponerTexto(
                "loteActual",
                "--"
            );

            ponerTexto(
                "inicioActual",
                "--"
            );

            ponerTexto(
                "tiempoActual",
                "--"
            );

            ponerTexto(
                "observacionesActuales",
                "--"
            );

            inicioProcesoMs = null;


            if (btnIniciar) {
                btnIniciar.disabled = false;
            }

            if (btnFinalizar) {
                btnFinalizar.disabled = true;
            }

            return;
        }


        // =================================================
        // PROCESO ACTIVO
        // =================================================

        const proceso =
            data.proceso;


        if (estado) {

            estado.innerHTML =
                "<strong>PROCESO ACTIVO</strong>";
        }


        ponerTexto(
            "loteActual",
            proceso.lote || "--"
        );


        ponerTexto(
            "inicioActual",
            formatoFecha(
                proceso.inicio
            )
        );


        ponerTexto(
            "observacionesActuales",
            proceso.observaciones ||
            "--"
        );


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


        ponerTexto(
            "estadoProceso",
            "Error consultando proceso"
        );
    }
}


// =========================================================
// RESUMEN DE CICLOS
// =========================================================

function pintarResumen(
    resumen,
    ciclos
) {

    resumen =
        resumen || {};


    const lista =
        Array.isArray(ciclos)
            ? ciclos
            : [];


    const cerrados =
        lista.filter(
            ciclo =>
                ciclo.estado === "CERRADO"
        );


    // -----------------------------------------------------
    // El endpoint histórico puede no traer
    // ultimo_intervalo_s.
    // Lo calculamos desde los ciclos.
    // -----------------------------------------------------

    let ultimoIntervalo =
        resumen.ultimo_intervalo_s;


    if (
        ultimoIntervalo === null ||
        ultimoIntervalo === undefined
    ) {

        const intervalos =
            cerrados
                .map(
                    ciclo =>
                        ciclo
                            .intervalo_purgas_segundos
                )
                .filter(
                    valor =>
                        valor !== null &&
                        valor !== undefined &&
                        !isNaN(Number(valor))
                );


        if (intervalos.length > 0) {

            ultimoIntervalo =
                intervalos[
                    intervalos.length - 1
                ];
        }
    }


    ponerTexto(
        "kpiCiclos",
        resumen.ciclos !== undefined
            ? resumen.ciclos
            : cerrados.length
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
            ultimoIntervalo
        )
    );
}


// =========================================================
// ORIGEN DEL ANÁLISIS
// =========================================================

function pintarOrigen(data) {

    const proceso =
        data.proceso;


    if (!proceso) {

        if (
            modoCiclos === "activo"
        ) {

            ponerTexto(
                "origenCiclos",
                "No existe un proceso activo."
            );

        } else {

            ponerTexto(
                "origenCiclos",
                "No existe el proceso histórico seleccionado."
            );
        }

        return;
    }


    if (
        modoCiclos === "historico"
    ) {

        ponerTexto(
            "origenCiclos",
            (
                "Proceso histórico"
                +
                " | Proceso ID "
                +
                proceso.id
                +
                " | Lote "
                +
                (
                    proceso.lote ||
                    "--"
                )
                +
                " | Estado "
                +
                (
                    proceso.estado ||
                    "--"
                )
            )
        );

    } else {

        ponerTexto(
            "origenCiclos",
            (
                "Proceso activo"
                +
                " | Proceso ID "
                +
                proceso.id
                +
                " | Lote "
                +
                (
                    proceso.lote ||
                    "--"
                )
            )
        );
    }
}


// =========================================================
// TABLA CICLOS
// =========================================================

function pintarTabla(ciclos) {

    const tbody =
        elemento("tablaCiclos");


    if (!tbody) {
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
                    ${escaparHtml(
                        ciclo.estado || "--"
                    )}
                </td>

            </tr>
            `;
    }


    tbody.innerHTML = html;
}


// =========================================================
// CARGAR CICLOS
//
// ACTIVO:
// /api/proceso/ciclos?modo=activo
//
// HISTÓRICO:
// /api/procesos/{id}/ciclos
// =========================================================

async function cargarCiclos() {

    try {

        ponerTexto(
            "origenCiclos",
            "Consultando ciclos..."
        );


        let url;


        if (
            modoCiclos === "historico" &&
            procesoHistoricoSeleccionado !== null
        ) {

            url =
                `/api/procesos/${procesoHistoricoSeleccionado}/ciclos`;

        } else {

            modoCiclos =
                "activo";

            procesoHistoricoSeleccionado =
                null;

            url =
                "/api/proceso/ciclos?modo=activo";
        }


        const response =
            await fetch(
                url,
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando ciclos"
            );
        }


        pintarResumen(
            data.resumen,
            data.ciclos
        );


        pintarOrigen(data);


        pintarTabla(
            data.ciclos
        );


        const btnActivo =
            elemento(
                "btnCiclosActivo"
            );


        if (btnActivo) {

            btnActivo.disabled =
                modoCiclos === "activo";
        }


    } catch (error) {

        console.error(
            "Error cargarCiclos:",
            error
        );


        ponerTexto(
            "origenCiclos",
            (
                "Error consultando ciclos: "
                +
                error.message
            )
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


// =========================================================
// VOLVER A PROCESO ACTIVO
// =========================================================

async function cambiarModoCiclos(modo) {

    if (modo !== "activo") {
        return;
    }


    modoCiclos =
        "activo";


    procesoHistoricoSeleccionado =
        null;


    await cargarCiclos();


    await cargarHistorialProcesos();
}


// =========================================================
// HISTORIAL DE PROCESOS
// =========================================================

async function cargarHistorialProcesos() {

    const tbody =
        elemento(
            "tablaProcesos"
        );


    if (!tbody) {
        return;
    }


    try {

        tbody.innerHTML =
            `
            <tr>
                <td colspan="8">
                    Consultando procesos...
                </td>
            </tr>
            `;


        const response =
            await fetch(
                "/api/procesos?limite=100",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando procesos"
            );
        }


        const procesos =
            Array.isArray(
                data.procesos
            )
                ? data.procesos
                : [];


        if (
            procesos.length === 0
        ) {

            tbody.innerHTML =
                `
                <tr>
                    <td colspan="8">
                        No hay procesos registrados.
                    </td>
                </tr>
                `;

            return;
        }


        let html = "";


        for (
            const proceso
            of procesos
        ) {

            const seleccionado =
                (
                    modoCiclos === "historico"
                    &&
                    procesoHistoricoSeleccionado ===
                    Number(proceso.id)
                );


            html +=
                `
                <tr
                    ${
                        seleccionado
                            ?
                            'style="background:#eef6ff;"'
                            :
                            ""
                    }
                >

                    <td>
                        ${proceso.id}
                    </td>

                    <td>
                        ${escaparHtml(
                            proceso.lote ||
                            "--"
                        )}
                    </td>

                    <td>
                        ${formatoFecha(
                            proceso.inicio
                        )}
                    </td>

                    <td>
                        ${formatoFecha(
                            proceso.fin
                        )}
                    </td>

                    <td>
                        ${formatoDuracion(
                            proceso.duracion_segundos
                        )}
                    </td>

                    <td>
                        ${escaparHtml(
                            proceso.estado ||
                            "--"
                        )}
                    </td>

                    <td>
                        ${
                            Number(
                                proceso.ciclos_cerrados ||
                                0
                            )
                        }
                    </td>

                    <td>

                        <button
                            type="button"
                            onclick="verProcesoHistorico(
                                ${proceso.id}
                            )"
                        >
                            Ver
                        </button>

                    </td>

                </tr>
                `;
        }


        tbody.innerHTML = html;


    } catch (error) {

        console.error(
            "Error cargarHistorialProcesos:",
            error
        );


        tbody.innerHTML =
            `
            <tr>
                <td colspan="8">
                    Error consultando procesos.
                </td>
            </tr>
            `;
    }
}


// =========================================================
// VER PROCESO HISTÓRICO
// =========================================================

async function verProcesoHistorico(
    procesoId
) {

    modoCiclos =
        "historico";


    procesoHistoricoSeleccionado =
        Number(
            procesoId
        );


    // Cargar el histórico seleccionado.

    await cargarCiclos();


    // Volver a pintar tabla para marcar
    // visualmente el proceso seleccionado.

    await cargarHistorialProcesos();


    // Llevar al usuario a los indicadores.

    const panel =
        elemento(
            "panelIndicadoresCiclos"
        );


    if (panel) {

        panel.scrollIntoView(
            {
                behavior: "smooth",
                block: "start"
            }
        );
    }
}


// =========================================================
// INICIAR PROCESO
// =========================================================

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
                "Error iniciando proceso."
            );

            return;
        }


        ponerTexto(
            "mensajeProceso",
            "Proceso iniciado correctamente."
        );


        // Al iniciar un proceso nuevo
        // volvemos a mostrar el proceso activo.

        modoCiclos =
            "activo";


        procesoHistoricoSeleccionado =
            null;


        await cargarProceso();

        await cargarCiclos();

        await cargarHistorialProcesos();


    } catch (error) {

        console.error(
            "Error iniciarProceso:",
            error
        );


        ponerTexto(
            "mensajeProceso",
            "Error iniciando proceso."
        );
    }
}


// =========================================================
// FINALIZAR PROCESO
// =========================================================

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
                "Error finalizando proceso."
            );

            return;
        }


        ponerTexto(
            "mensajeProceso",
            "Proceso finalizado."
        );


        await cargarProceso();

        await cargarHistorialProcesos();


        if (
            modoCiclos === "activo"
        ) {

            await cargarCiclos();
        }


    } catch (error) {

        console.error(
            "Error finalizarProceso:",
            error
        );


        ponerTexto(
            "mensajeProceso",
            "Error finalizando proceso."
        );
    }
}


// =========================================================
// INICIO PÁGINA
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    async function() {

        console.log(
            "proceso.js MDFR historial cargado"
        );


        await cargarProceso();

        await cargarCiclos();

        await cargarHistorialProcesos();
    }
);


// =========================================================
// ACTUALIZACIONES AUTOMÁTICAS
// =========================================================

// Cronómetro proceso activo.

setInterval(
    actualizarCronometro,
    1000
);


// Ciclos.
//
// IMPORTANTE:
// Si estamos viendo histórico,
// vuelve a consultar EL MISMO proceso histórico.
// Ya no regresa automáticamente al activo.

setInterval(
    cargarCiclos,
    30000
);


// Lista de procesos.

setInterval(
    cargarHistorialProcesos,
    60000
);