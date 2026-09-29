// =========================================================
// UTILIDADES
// =========================================================

function mostrarValor(
    id,
    dato,
    unidadEsperada
) {

    const elemento =
        document.getElementById(
            id
        );


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


    const valor =
        Number(
            dato.valor
        );


    if (
        !Number.isFinite(
            valor
        )
    ) {

        elemento.innerText =
            "Sin datos";

        return;
    }


    let textoValor;


    if (
        unidadEsperada ===
        "ppm"
    ) {

        textoValor =
            valor.toFixed(
                0
            );

    }

    else {

        textoValor =
            valor.toFixed(
                1
            );
    }


    elemento.innerText =
        `${textoValor} ${unidadEsperada}`;
}



function formatoFecha(
    timestamp
) {

    if (!timestamp) {
        return "--";
    }


    const fecha =
        new Date(
            timestamp
        );


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



// =========================================================
// MEDICIONES ACTUALES
// =========================================================

async function actualizarValores() {

    try {

        const response =
            await fetch(
                "/api/actual",
                {
                    cache:
                        "no-store"
                }
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


        // =============================================
        // ÚLTIMA ACTUALIZACIÓN
        // =============================================

        let ultimaFecha =
            null;


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
                        ultimaFecha
                        .toISOString()
                    );

            }

            else {

                elemento.innerText =
                    "Sin datos";
            }
        }


    }

    catch (error) {

        console.error(
            "Error actualizando valores:",
            error
        );
    }
}



// =========================================================
// PROCESO DE MADURACIÓN
// =========================================================

let inicioProcesoHomeMs =
    null;



function formatoDuracionHome(
    segundos
) {

    if (
        segundos === null ||
        segundos === undefined ||
        isNaN(
            Number(
                segundos
            )
        )
    ) {

        return "--";
    }


    let total =
        Math.max(
            0,
            Math.floor(
                Number(
                    segundos
                )
            )
        );


    const dias =
        Math.floor(
            total /
            86400
        );


    total %=
        86400;


    const horas =
        Math.floor(
            total /
            3600
        );


    total %=
        3600;


    const minutos =
        Math.floor(
            total /
            60
        );


    const segundosRestantes =
        total %
        60;


    if (
        dias > 0
    ) {

        return (
            dias +
            " d " +
            String(
                horas
            ).padStart(
                2,
                "0"
            ) +
            ":" +
            String(
                minutos
            ).padStart(
                2,
                "0"
            ) +
            ":" +
            String(
                segundosRestantes
            ).padStart(
                2,
                "0"
            )
        );
    }


    return (
        String(
            horas
        ).padStart(
            2,
            "0"
        ) +
        ":" +
        String(
            minutos
        ).padStart(
            2,
            "0"
        ) +
        ":" +
        String(
            segundosRestantes
        ).padStart(
            2,
            "0"
        )
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


    if (
        inicioProcesoHomeMs ===
        null
    ) {

        elemento.innerText =
            "--";

        return;
    }


    const segundos =
        (
            Date.now() -
            inicioProcesoHomeMs
        ) /
        1000;


    elemento.innerText =
        formatoDuracionHome(
            segundos
        );
}



function actualizarBotonesProceso(
    activo
) {

    const btnIniciar =
        document.getElementById(
            "btnIniciarProcesoHome"
        );


    const btnFinalizar =
        document.getElementById(
            "btnFinalizarProcesoHome"
        );


    if (btnIniciar) {

        btnIniciar.disabled =
            activo;
    }


    if (btnFinalizar) {

        btnFinalizar.disabled =
            !activo;
    }
}



async function actualizarProcesoHome() {

    try {

        const responseProceso =
            await fetch(
                "/api/proceso/actual",
                {
                    cache:
                        "no-store"
                }
            );


        const dataProceso =
            await responseProceso
                .json();


        if (
            !responseProceso.ok
        ) {

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


        // =============================================
        // SIN PROCESO ACTIVO
        // =============================================

        if (
            !dataProceso.activo ||
            !dataProceso.proceso
        ) {

            if (estado) {

                estado.innerText =
                    "SIN PROCESO";

                estado.className =
                    "process-status estado-inactivo";
            }


            if (inicio) {

                inicio.innerText =
                    "--";
            }


            inicioProcesoHomeMs =
                null;


            actualizarBotonesProceso(
                false
            );


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
                    "0";
            }


            if (ultimo) {
                ultimo.innerText =
                    "--";
            }


            actualizarTiempoProcesoHome();

            return;
        }


        // =============================================
        // PROCESO ACTIVO
        // =============================================

        const proceso =
            dataProceso.proceso;


        if (estado) {

            estado.innerText =
                "ACTIVO";

            estado.className =
                "process-status estado-activo";
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


        actualizarBotonesProceso(
            true
        );


        actualizarTiempoProcesoHome();


        // =============================================
        // CICLOS CO2
        // =============================================

        const responseCiclos =
            await fetch(
                "/api/proceso/ciclos?modo=activo",
                {
                    cache:
                        "no-store"
                }
            );


        const dataCiclos =
            await responseCiclos
                .json();


        if (
            !responseCiclos.ok
        ) {

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
                (
                    dataCiclos.resumen &&
                    dataCiclos.resumen
                        .ciclos !==
                    undefined
                )

                    ?
                    dataCiclos.resumen
                        .ciclos

                    :
                    0;
        }


        if (ultimo) {

            const valor =
                dataCiclos.resumen
                    ?
                    dataCiclos.resumen
                        .low_high_promedio_s
                    :
                    null;


            ultimo.innerText =
                formatoDuracionHome(
                    valor
                );
        }


    }

    catch (error) {

        console.error(
            "Error actualizando proceso home:",
            error
        );
    }
}



// =========================================================
// INICIAR PROCESO DESDE HOME
// =========================================================

async function iniciarProcesoHome() {

    const confirmar =
        window.confirm(
            "¿Desea INICIAR un nuevo proceso de maduración?"
        );


    if (!confirmar) {
        return;
    }


    const mensaje =
        document.getElementById(
            "mensajeProcesoHome"
        );


    if (mensaje) {

        mensaje.innerText =
            "Iniciando proceso...";
    }


    try {

        const form =
            new FormData();


        form.append(
            "lote",
            ""
        );


        form.append(
            "observaciones",
            "Proceso iniciado manualmente desde Inicio"
        );


        const response =
            await fetch(
                "/api/proceso/iniciar",
                {
                    method:
                        "POST",

                    body:
                        form
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "No se pudo iniciar el proceso"
            );
        }


        if (mensaje) {

            mensaje.innerText =
                "Proceso iniciado correctamente.";
        }


        await actualizarProcesoHome();


    }

    catch (error) {

        console.error(
            "Error iniciando proceso:",
            error
        );


        if (mensaje) {

            mensaje.innerText =
                error.message;
        }
    }
}



// =========================================================
// FINALIZAR PROCESO DESDE HOME
// =========================================================

async function finalizarProcesoHome() {

    const confirmar =
        window.confirm(
            "¿Desea FINALIZAR el proceso de maduración actual?"
        );


    if (!confirmar) {
        return;
    }


    const mensaje =
        document.getElementById(
            "mensajeProcesoHome"
        );


    if (mensaje) {

        mensaje.innerText =
            "Finalizando proceso...";
    }


    try {

        const response =
            await fetch(
                "/api/proceso/finalizar",
                {
                    method:
                        "POST"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "No se pudo finalizar el proceso"
            );
        }


        if (mensaje) {

            mensaje.innerText =
                "Proceso finalizado correctamente.";
        }


        inicioProcesoHomeMs =
            null;


        await actualizarProcesoHome();


    }

    catch (error) {

        console.error(
            "Error finalizando proceso:",
            error
        );


        if (mensaje) {

            mensaje.innerText =
                error.message;
        }
    }
}



// =========================================================
// CALIDAD DE DATOS
// =========================================================

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


    if (
        segundos < 60
    ) {

        return (
            `${Math.round(segundos)} s`
        );
    }


    const minutos =
        segundos /
        60;


    if (
        minutos < 60
    ) {

        return (
            `${Math.round(minutos)} min`
        );
    }


    const horas =
        minutos /
        60;


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
            "info-value estado-alerta";

        return;
    }


    const edad =
        formatoEdadDato(
            dato.edad_segundos
        );


    if (
        dato.estado ===
        "OK"
    ) {

        elemento.innerText =
            `OK · hace ${edad}`;

        elemento.className =
            "info-value estado-activo";

    }

    else if (
        dato.estado ===
        "ATRASADO"
    ) {

        elemento.innerText =
            `ATRASADO · hace ${edad}`;

        elemento.className =
            "info-value estado-alerta";

    }

    else {

        elemento.innerText =
            `SIN DATOS · hace ${edad}`;

        elemento.className =
            "info-value estado-alerta";
    }
}



// =========================================================
// ESTADO OPERATIVO
// =========================================================

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


            if (
                estado ===
                "CERRADA"
            ) {

                puerta.style.color =
                    "#15803d";

            }

            else {

                puerta.style.color =
                    "#b91c1c";
            }
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
                    ?.activo ===
                true;


            man.innerText =
                activo
                    ?
                    "ACTIVO"
                    :
                    "NORMAL";


            man.style.color =
                activo
                    ?
                    "#b91c1c"
                    :
                    "#15803d";
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


    }

    catch (error) {

        console.error(
            "Error actualizarEstadoOperacion:",
            error
        );
    }
}



// =========================================================
// SALUD DEL SISTEMA
// =========================================================

async function actualizarSaludSistema() {

    try {

        const response =
            await fetch(
                "/api/sistema",
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

                internet.style.color =
                    "#15803d";

            }

            else {

                internet.innerText =
                    "SIN INTERNET";

                internet.style.color =
                    "#b91c1c";
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
                    data.aws
                        ?.pendientes ??
                    0
                );


            aws.innerText =
                pendientes;


            aws.style.color =
                (
                    pendientes ===
                    0
                )
                    ?
                    "#15803d"
                    :
                    "#b91c1c";
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
                data.database
                    ?.estado ||
                "--";


            db.innerText =
                estado;


            db.style.color =
                (
                    estado ===
                    "OK"
                )
                    ?
                    "#15803d"
                    :
                    "#b91c1c";
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

                cpu.style.color =
                    "#64748b";

            }

            else {

                cpu.innerText =
                    `${temp} °C`;


                cpu.style.color =
                    (
                        temp < 70
                    )
                        ?
                        "#15803d"
                        :
                        "#b91c1c";
            }
        }


    }

    catch (error) {

        console.error(
            "Error actualizarSaludSistema:",
            error
        );
    }
}



// =========================================================
// ACTUADORES - COLOR VISUAL
// =========================================================

function pintarActuador(
    idElemento,
    estado
) {

    const elemento =
        document.getElementById(
            idElemento
        );


    if (!elemento) {
        return;
    }


    const texto =
        elemento.querySelector(
            ".status-text"
        );


    elemento.classList.remove(
        "state-on",
        "state-off",
        "state-unknown"
    );


    // =============================================
    // ON = VERDE
    // =============================================

    if (
        estado ===
        "ON"
    ) {

        elemento.classList.add(
            "state-on"
        );


        if (texto) {

            texto.innerText =
                "ON";
        }


        return;
    }


    // =============================================
    // OFF = ROJO
    // =============================================

    if (
        estado ===
        "OFF"
    ) {

        elemento.classList.add(
            "state-off"
        );


        if (texto) {

            texto.innerText =
                "OFF";
        }


        return;
    }


    // =============================================
    // SIN DATOS = GRIS
    // =============================================

    elemento.classList.add(
        "state-unknown"
    );


    if (texto) {

        texto.innerText =
            "SIN DATOS";
    }
}



// =========================================================
// ACTUADORES
// =========================================================

async function actualizarActuadores() {

    try {

        const response =
            await fetch(
                "/api/actuadores",
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
                "Error consultando actuadores"
            );
        }


        const actuadores =
            data.actuadores ||
            {};


        // =============================================
        // MAPA API -> HTML
        // =============================================

        const mapa = {

            recircular:
                "estadoRecircular",

            extractor:
                "estadoExtractor",

            humidificador:
                "estadoHumidificador",

            etileno:
                "estadoEtileno",

            aire_fresco:
                "estadoAireFresco"
        };


        // =============================================
        // PINTAR ESTADOS
        // =============================================

        for (
            const [
                nombre,
                idElemento
            ]
            of
            Object.entries(
                mapa
            )
        ) {

            const actuador =
                actuadores[
                    nombre
                ];


            pintarActuador(
                idElemento,
                actuador
                    ?
                    actuador.estado
                    :
                    null
            );
        }


        // =============================================
        // TIMESTAMP
        // =============================================

        const actualizacion =
            document.getElementById(
                "actualizacionActuadores"
            );


        if (actualizacion) {

            if (
                data.timestamp
            ) {

                actualizacion.innerText =
                    "Última lectura: " +
                    formatoFecha(
                        data.timestamp
                    );

            }

            else {

                actualizacion.innerText =
                    "Última lectura: --";
            }
        }


    }

    catch (error) {

        console.error(
            "Error actualizando actuadores:",
            error
        );


        const ids = [

            "estadoRecircular",
            "estadoExtractor",
            "estadoHumidificador",
            "estadoEtileno",
            "estadoAireFresco"

        ];


        for (
            const id
            of ids
        ) {

            pintarActuador(
                id,
                null
            );
        }


        const actualizacion =
            document.getElementById(
                "actualizacionActuadores"
            );


        if (actualizacion) {

            actualizacion.innerText =
                "No se pudo consultar el estado de actuadores.";
        }
    }
}



// =========================================================
// PRIMERA CARGA
// =========================================================

actualizarValores();

actualizarProcesoHome();

actualizarEstadoOperacion();

actualizarSaludSistema();

actualizarActuadores();



// =========================================================
// ACTUALIZACIONES PERIÓDICAS
// =========================================================

setInterval(
    actualizarValores,
    10000
);


setInterval(
    actualizarProcesoHome,
    10000
);


setInterval(
    actualizarEstadoOperacion,
    10000
);


setInterval(
    actualizarActuadores,
    10000
);


setInterval(
    actualizarSaludSistema,
    30000
);


setInterval(
    actualizarTiempoProcesoHome,
    1000
);