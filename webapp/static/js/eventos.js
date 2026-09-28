function elemento(id) {
    return document.getElementById(id);
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


async function cargarTiposEvento() {

    try {

        const response =
            await fetch(
                "/api/eventos/tipos",
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando tipos de evento"
            );
        }

        const select =
            elemento(
                "tipoEvento"
            );

        if (!select) {
            return;
        }

        const valorActual =
            select.value;

        select.innerHTML =
            '<option value="TODOS">Todos</option>';

        const tipos =
            Array.isArray(data.tipos)
                ? data.tipos
                : [];

        for (const tipo of tipos) {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                tipo;

            option.textContent =
                tipo;

            select.appendChild(
                option
            );
        }

        if (
            valorActual &&
            [
                ...select.options
            ].some(
                opcion =>
                    opcion.value ===
                    valorActual
            )
        ) {

            select.value =
                valorActual;
        }

    } catch (error) {

        console.error(
            "Error cargarTiposEvento:",
            error
        );
    }
}


function construirParametros() {

    const params =
        new URLSearchParams();

    const tipo =
        elemento(
            "tipoEvento"
        )?.value;

    const desde =
        elemento(
            "fechaDesdeEvento"
        )?.value;

    const hasta =
        elemento(
            "fechaHastaEvento"
        )?.value;

    const limite =
        elemento(
            "limiteEventos"
        )?.value ||
        "100";


    params.set(
        "limite",
        limite
    );


    if (
        tipo &&
        tipo !== "TODOS"
    ) {

        params.set(
            "tipo",
            tipo
        );
    }


    if (desde) {

        params.set(
            "desde",
            desde
        );
    }


    if (hasta) {

        params.set(
            "hasta",
            hasta
        );
    }


    return params;
}


function pintarEventos(
    eventos
) {

    const tbody =
        elemento(
            "tablaEventos"
        );

    if (!tbody) {
        return;
    }

    if (
        !Array.isArray(eventos) ||
        eventos.length === 0
    ) {

        tbody.innerHTML =
            `
            <tr>
                <td colspan="5">
                    No hay eventos para los filtros seleccionados.
                </td>
            </tr>
            `;

        return;
    }

    let html = "";

    for (
        const evento
        of eventos
    ) {

        const timestamp =
            evento.timestamp ||
            evento.timestamp_utc ||
            null;

        const fecha =
            formatoFecha(
                timestamp
            );

        const tipo =
            evento.tipo ??
            "--";

        const estado =
            evento.estado ??
            "--";

        const valor =
            evento.valor ??
            "--";

        const detalle =
            evento.detalle ??
            "--";

        html +=
            `
            <tr>

                <td>
                    ${escaparHtml(fecha)}
                </td>

                <td>
                    ${escaparHtml(tipo)}
                </td>

                <td>
                    ${escaparHtml(estado)}
                </td>

                <td>
                    ${escaparHtml(valor)}
                </td>

                <td>
                    ${escaparHtml(detalle)}
                </td>

            </tr>
            `;
    }

    tbody.innerHTML =
        html;
}


async function consultarEventos() {

    const resumen =
        elemento(
            "resumenEventos"
        );

    const tbody =
        elemento(
            "tablaEventos"
        );

    try {

        if (resumen) {

            resumen.innerText =
                "Consultando...";
        }


        if (tbody) {

            tbody.innerHTML =
                `
                <tr>
                    <td colspan="5">
                        Consultando eventos...
                    </td>
                </tr>
                `;
        }


        const params =
            construirParametros();


        const response =
            await fetch(
                "/api/eventos?" +
                params.toString(),
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error consultando eventos"
            );
        }


        const eventos =
            Array.isArray(
                data.eventos
            )
                ? data.eventos
                : [];


        pintarEventos(
            eventos
        );


        if (resumen) {

            resumen.innerText =
                `${data.cantidad ?? eventos.length} evento(s) encontrado(s)`;
        }


    } catch (error) {

        console.error(
            "Error consultarEventos:",
            error
        );


        if (resumen) {

            resumen.innerText =
                "Error consultando eventos: " +
                error.message;
        }


        if (tbody) {

            tbody.innerHTML =
                `
                <tr>
                    <td colspan="5">
                        Error consultando eventos.
                    </td>
                </tr>
                `;
        }
    }
}


function limpiarFiltrosEventos() {

    const tipo =
        elemento(
            "tipoEvento"
        );

    const desde =
        elemento(
            "fechaDesdeEvento"
        );

    const hasta =
        elemento(
            "fechaHastaEvento"
        );

    const limite =
        elemento(
            "limiteEventos"
        );


    if (tipo) {

        tipo.value =
            "TODOS";
    }


    if (desde) {

        desde.value =
            "";
    }


    if (hasta) {

        hasta.value =
            "";
    }


    if (limite) {

        limite.value =
            "100";
    }


    consultarEventos();
}


document.addEventListener(
    "DOMContentLoaded",
    async function() {

        await cargarTiposEvento();

        await consultarEventos();
    }
);