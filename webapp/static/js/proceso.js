let inicioProcesoMs = null;


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

    segundos = Math.max(
        0,
        Math.floor(segundos)
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

    return (
        `${dias} d ` +
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
}


cargarProceso();

setInterval(
    actualizarCronometro,
    1000
);