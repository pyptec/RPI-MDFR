// =========================================================
// VARIABLE HISTÓRICA
// =========================================================

let variableActual = {

    sensor:
        "CT01CO2",

    variable:
        "co2",

    titulo:
        "CO₂",

    unidad:
        "ppm"
};


// =========================================================
// MDFR PROCESS
// =========================================================

let mdfrModo =
    "activo";


let mdfrProcesoId =
    null;


// =========================================================
// HORAS
// =========================================================

function cargarHoras() {

    const desde =
        document.getElementById(
            "horaDesde"
        );


    const hasta =
        document.getElementById(
            "horaHasta"
        );


    desde.innerHTML =
        "";


    hasta.innerHTML =
        "";


    for (
        let h = 0;
        h < 24;
        h++
    ) {

        const texto =
            String(
                h
            ).padStart(
                2,
                "0"
            );


        desde.add(
            new Option(
                texto,
                texto
            )
        );


        hasta.add(
            new Option(
                texto,
                texto
            )
        );
    }
}


// =========================================================
// FECHA ACTUAL
// =========================================================

function fechaHoy() {

    const ahora =
        new Date();


    const year =
        ahora.getFullYear();


    const month =
        String(
            ahora.getMonth() + 1
        ).padStart(
            2,
            "0"
        );


    const day =
        String(
            ahora.getDate()
        ).padStart(
            2,
            "0"
        );


    return (
        `${year}-${month}-${day}`
    );
}


// =========================================================
// CONFIGURACIÓN INICIAL
// =========================================================

function configurarInicial() {

    cargarHoras();


    const hoy =
        fechaHoy();


    document.getElementById(
        "fechaDesde"
    ).value =
        hoy;


    document.getElementById(
        "fechaHasta"
    ).value =
        hoy;


    const ahora =
        new Date();


    let horaHasta =
        ahora.getHours();


    let horaDesde =
        horaHasta -
        2;


    if (
        horaDesde < 0
    ) {

        horaDesde =
            0;
    }


    document.getElementById(
        "horaDesde"
    ).value =
        String(
            horaDesde
        ).padStart(
            2,
            "0"
        );


    document.getElementById(
        "horaHasta"
    ).value =
        String(
            horaHasta
        ).padStart(
            2,
            "0"
        );


    const minuto =
        Math.floor(
            ahora.getMinutes() /
            10
        )
        *
        10;


    document.getElementById(
        "minDesde"
    ).value =
        String(
            minuto
        ).padStart(
            2,
            "0"
        );


    document.getElementById(
        "minHasta"
    ).value =
        String(
            minuto
        ).padStart(
            2,
            "0"
        );
}


// =========================================================
// FECHA / HORA DEL FILTRO
// =========================================================

function obtenerFechaHora(
    prefijo
) {

    const fecha =
        document.getElementById(
            `fecha${prefijo}`
        ).value;


    const hora =
        document.getElementById(
            `hora${prefijo}`
        ).value;


    const minuto =
        document.getElementById(
            `min${prefijo}`
        ).value;


    return (
        `${fecha}T${hora}:${minuto}`
    );
}


// =========================================================
// FECHA COLOMBIA
// =========================================================

function formatoColombia(
    timestamp
) {

    if (
        !timestamp
    ) {

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
// FECHA CORTA
// =========================================================

function formatoFechaCorta(
    timestamp
) {

    if (
        !timestamp
    ) {

        return "--";
    }


    return new Date(
        timestamp
    ).toLocaleString(
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

            hour12:
                false
        }
    );
}


// =========================================================
// HORA
// =========================================================

function formatoHoraColombia(
    timestamp
) {

    if (
        !timestamp
    ) {

        return "--";
    }


    return new Date(
        timestamp
    ).toLocaleTimeString(
        "es-CO",
        {
            timeZone:
                "America/Bogota",

            hour:
                "2-digit",

            minute:
                "2-digit",

            hour12:
                false
        }
    );
}


// =========================================================
// DURACIÓN
// =========================================================

function formatoDuracion(
    segundos
) {

    if (
        segundos === null ||
        segundos === undefined ||
        !Number.isFinite(
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
            Math.round(
                Number(
                    segundos
                )
            )
        );


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


    return (
        String(
            horas
        ).padStart(
            2,
            "0"
        )
        +
        ":"
        +
        String(
            minutos
        ).padStart(
            2,
            "0"
        )
        +
        ":"
        +
        String(
            segundosRestantes
        ).padStart(
            2,
            "0"
        )
    );
}


// =========================================================
// SEGUNDOS A HORAS
// =========================================================

function segundosAHoras(
    segundos
) {

    if (
        segundos === null ||
        segundos === undefined
    ) {

        return null;
    }


    const valor =
        Number(
            segundos
        );


    if (
        !Number.isFinite(
            valor
        )
    ) {

        return null;
    }


    return (
        valor /
        3600
    );
}


// =========================================================
// SELECCIONAR VARIABLE
// =========================================================

function seleccionarVariable(
    sensor,
    variable,
    titulo,
    unidad
) {

    variableActual = {

        sensor,
        variable,
        titulo,
        unidad
    };


    const tituloGrafica =
        document.getElementById(
            "tituloGrafica"
        );


    if (
        tituloGrafica
    ) {

        tituloGrafica.innerText =
            titulo;
    }


    consultarHistorico();
}


// =========================================================
// VARIABLES
// =========================================================

function consultarCO2() {

    seleccionarVariable(
        "CT01CO2",
        "co2",
        "CO₂",
        "ppm"
    );
}


function consultarTemperatura() {

    seleccionarVariable(
        "THT03R",
        "temperatura",
        "Temperatura ambiente",
        "°C"
    );
}


function consultarHumedad() {

    seleccionarVariable(
        "THT03R",
        "humedad",
        "Humedad relativa",
        "%"
    );
}


function consultarC2H4() {

    seleccionarVariable(
        "C2H4",
        "c2h4",
        "Etileno C₂H₄",
        "ppm"
    );
}


function consultarPT100() {

    seleccionarVariable(
        "PT21A01",
        "temperatura",
        "PT100",
        "°C"
    );
}


function consultarPT1000() {

    seleccionarVariable(
        "CWT",
        "temperatura_ch1",
        "PT1000",
        "°C"
    );
}


// =========================================================
// CONSULTAR HISTÓRICO
// =========================================================

async function consultarHistorico() {

    const desde =
        obtenerFechaHora(
            "Desde"
        );


    const hasta =
        obtenerFechaHora(
            "Hasta"
        );


    if (
        !desde ||
        !hasta
    ) {

        mostrarResultado(
            "Seleccione el rango de fechas."
        );


        return;
    }


    const url =
        "/api/historico"
        +
        `?sensor=${encodeURIComponent(
            variableActual.sensor
        )}`
        +
        `&variable=${encodeURIComponent(
            variableActual.variable
        )}`
        +
        `&desde=${encodeURIComponent(
            desde
        )}`
        +
        `&hasta=${encodeURIComponent(
            hasta
        )}`;


    mostrarResultado(
        "Consultando..."
    );


    try {

        const response =
            await fetch(
                url,
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            mostrarResultado(
                data.detail ||
                "Error consultando datos."
            );


            limpiarGrafica();


            return;
        }


        if (
            !data.datos ||
            data.datos.length === 0
        ) {

            mostrarResultado(
                `No hay datos de ${variableActual.titulo} para este período.`
            );


            dibujarGrafica(
                [],
                variableActual.titulo,
                variableActual.unidad
            );


            return;
        }


        mostrarResultado(
            `${data.cantidad} mediciones encontradas`
        );


        dibujarGrafica(
            data.datos,
            variableActual.titulo,
            variableActual.unidad
        );

    }

    catch (
        error
    ) {

        console.error(
            error
        );


        mostrarResultado(
            "Error comunicándose con el servidor."
        );


        limpiarGrafica();
    }
}


// =========================================================
// RESULTADO
// =========================================================

function mostrarResultado(
    texto
) {

    const resultado =
        document.getElementById(
            "resultado"
        );


    if (
        resultado
    ) {

        resultado.innerHTML =
            texto;
    }
}


// =========================================================
// LIMPIAR GRÁFICA
// =========================================================

function limpiarGrafica() {

    const canvas =
        document.getElementById(
            "graficaCO2"
        );


    if (
        !canvas
    ) {

        return;
    }


    const ctx =
        canvas.getContext(
            "2d"
        );


    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );
}


// =========================================================
// GRÁFICA HISTÓRICA
// =========================================================

function dibujarGrafica(
    datos,
    titulo,
    unidad
) {

    const canvas =
        document.getElementById(
            "graficaCO2"
        );


    if (
        !canvas
    ) {

        return;
    }


    const ctx =
        canvas.getContext(
            "2d"
        );


    const W =
        canvas.width;


    const H =
        canvas.height;


    ctx.clearRect(
        0,
        0,
        W,
        H
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.strokeStyle =
        "#64748b";


    ctx.font =
        "14px Arial";


    if (
        !datos ||
        datos.length === 0
    ) {

        ctx.fillText(
            "No hay datos para este período.",
            40,
            60
        );


        return;
    }


    const valores =
        datos
        .map(
            dato =>
                Number(
                    dato.valor
                )
        )
        .filter(
            valor =>
                Number.isFinite(
                    valor
                )
        );


    if (
        valores.length === 0
    ) {

        return;
    }


    const minimoReal =
        Math.min(
            ...valores
        );


    const maximoReal =
        Math.max(
            ...valores
        );


    let margen =
        (
            maximoReal -
            minimoReal
        )
        *
        0.10;


    if (
        margen === 0
    ) {

        margen =
            Math.abs(
                maximoReal
            )
            *
            0.05;


        if (
            margen === 0
        ) {

            margen =
                1;
        }
    }


    const minimo =
        minimoReal -
        margen;


    const maximo =
        maximoReal +
        margen;


    const margenIzq =
        75;


    const margenDer =
        40;


    const margenSup =
        45;


    const margenInf =
        80;


    const ancho =
        W -
        margenIzq -
        margenDer;


    const alto =
        H -
        margenSup -
        margenInf;


    const rango =
        maximo -
        minimo;


    ctx.fillText(
        `${titulo} (${unidad})`,
        margenIzq,
        25
    );


    // EJES

    ctx.beginPath();


    ctx.moveTo(
        margenIzq,
        margenSup
    );


    ctx.lineTo(
        margenIzq,
        H -
        margenInf
    );


    ctx.lineTo(
        W -
        margenDer,
        H -
        margenInf
    );


    ctx.stroke();


    // ESCALA Y

    for (
        let i = 0;
        i <= 5;
        i++
    ) {

        const valor =
            maximo -
            (
                rango *
                i /
                5
            );


        const y =
            margenSup +
            (
                alto *
                i /
                5
            );


        ctx.beginPath();


        ctx.moveTo(
            margenIzq,
            y
        );


        ctx.lineTo(
            W -
            margenDer,
            y
        );


        ctx.stroke();


        ctx.fillText(
            valor.toFixed(
                unidad ===
                "ppm"
                    ?
                    0
                    :
                    1
            ),
            8,
            y + 4
        );
    }


    // PUNTOS

    const puntos =
        [];


    datos.forEach(
        (
            dato,
            indice
        ) => {

            const valor =
                Number(
                    dato.valor
                );


            if (
                !Number.isFinite(
                    valor
                )
            ) {

                return;
            }


            const x =
                margenIzq +
                (
                    indice /
                    Math.max(
                        datos.length -
                        1,
                        1
                    )
                )
                *
                ancho;


            const y =
                margenSup +
                (
                    1 -
                    (
                        valor -
                        minimo
                    )
                    /
                    rango
                )
                *
                alto;


            puntos.push(
                {
                    x,
                    y,
                    dato
                }
            );
        }
    );


    // LÍNEA

    if (
        puntos.length > 0
    ) {

        ctx.beginPath();


        puntos.forEach(
            (
                punto,
                indice
            ) => {

                if (
                    indice === 0
                ) {

                    ctx.moveTo(
                        punto.x,
                        punto.y
                    );

                }

                else {

                    ctx.lineTo(
                        punto.x,
                        punto.y
                    );
                }
            }
        );


        ctx.stroke();
    }


    // PUNTOS

    puntos.forEach(
        punto => {

            ctx.beginPath();


            ctx.arc(
                punto.x,
                punto.y,
                3,
                0,
                Math.PI *
                2
            );


            ctx.fill();
        }
    );


    // EJE X

    const etiquetas =
        Math.min(
            6,
            datos.length
        );


    for (
        let i = 0;
        i < etiquetas;
        i++
    ) {

        const indice =
            Math.round(
                i *
                (
                    datos.length -
                    1
                )
                /
                Math.max(
                    etiquetas -
                    1,
                    1
                )
            );


        const dato =
            datos[
                indice
            ];


        const x =
            margenIzq +
            (
                indice /
                Math.max(
                    datos.length -
                    1,
                    1
                )
            )
            *
            ancho;


        ctx.fillText(
            formatoHoraColombia(
                dato.timestamp
            ),
            x -
            20,
            H -
            45
        );
    }


    ctx.fillText(
        formatoColombia(
            datos[0]
                .timestamp
        ),
        margenIzq,
        H -
        15
    );


    ctx.fillText(
        formatoColombia(
            datos[
                datos.length -
                1
            ]
            .timestamp
        ),
        W -
        240,
        H -
        15
    );


    activarTooltip(
        canvas,
        puntos,
        unidad
    );
}


// =========================================================
// TOOLTIP
// =========================================================

function activarTooltip(
    canvas,
    puntos,
    unidad
) {

    canvas.onmousemove =
        function(
            event
        ) {

            const tooltip =
                document.getElementById(
                    "tooltipGrafica"
                );


            if (
                !tooltip
            ) {

                return;
            }


            const rect =
                canvas
                .getBoundingClientRect();


            const escalaX =
                canvas.width /
                rect.width;


            const escalaY =
                canvas.height /
                rect.height;


            const mouseX =
                (
                    event.clientX -
                    rect.left
                )
                *
                escalaX;


            const mouseY =
                (
                    event.clientY -
                    rect.top
                )
                *
                escalaY;


            let cercano =
                null;


            let distanciaMinima =
                18;


            puntos.forEach(
                punto => {

                    const dx =
                        mouseX -
                        punto.x;


                    const dy =
                        mouseY -
                        punto.y;


                    const distancia =
                        Math.sqrt(
                            dx *
                            dx
                            +
                            dy *
                            dy
                        );


                    if (
                        distancia <
                        distanciaMinima
                    ) {

                        cercano =
                            punto;


                        distanciaMinima =
                            distancia;
                    }
                }
            );


            if (
                !cercano
            ) {

                tooltip.style.display =
                    "none";


                return;
            }


            tooltip.style.display =
                "block";


            tooltip.innerHTML =
                `<strong>${formatoColombia(
                    cercano.dato.timestamp
                )}</strong><br>`
                +
                `${variableActual.titulo}: `
                +
                `${cercano.dato.valor} ${unidad}`;


            tooltip.style.left =
                `${event.pageX + 15}px`;


            tooltip.style.top =
                `${event.pageY + 15}px`;
        };


    canvas.onmouseleave =
        function() {

            const tooltip =
                document.getElementById(
                    "tooltipGrafica"
                );


            if (
                tooltip
            ) {

                tooltip.style.display =
                    "none";
            }
        };
}


// =========================================================
// LISTA DE PROCESOS MDFR
// =========================================================

async function cargarProcesosMdfr() {

    const selector =
        document.getElementById(
            "selectorMdfrProceso"
        );


    if (
        !selector
    ) {

        return;
    }


    try {

        const valorAnterior =
            selector.value;


        const response =
            await fetch(
                "/api/procesos?limite=100",
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(
                data.detail ||
                "Error consultando procesos."
            );
        }


        const procesos =
            Array.isArray(
                data.procesos
            )
                ?
                data.procesos
                :
                [];


        selector.innerHTML =
            "";


        if (
            procesos.length ===
            0
        ) {

            selector.innerHTML =
                `
                <option value="">
                    No hay procesos registrados
                </option>
                `;


            return;
        }


        for (
            const proceso
            of procesos
        ) {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                proceso.id;


            option.textContent =
                `ID ${proceso.id}`
                +
                ` | ${proceso.lote || "SIN-LOTE"}`
                +
                ` | ${formatoFechaCorta(
                    proceso.inicio
                )}`
                +
                ` | ${proceso.estado || "--"}`
                +
                ` | ${proceso.ciclos_cerrados || 0} ciclos`;


            selector.appendChild(
                option
            );
        }


        if (
            mdfrProcesoId !==
            null
        ) {

            selector.value =
                String(
                    mdfrProcesoId
                );

        }

        else if (
            valorAnterior
        ) {

            selector.value =
                valorAnterior;
        }

    }

    catch (
        error
    ) {

        console.error(
            "Error cargarProcesosMdfr:",
            error
        );


        selector.innerHTML =
            `
            <option value="">
                Error consultando procesos
            </option>
            `;
    }
}


// =========================================================
// ANALIZAR HISTÓRICO
// =========================================================

async function analizarMdfrHistorico() {

    const selector =
        document.getElementById(
            "selectorMdfrProceso"
        );


    if (
        !selector ||
        !selector.value
    ) {

        return;
    }


    mdfrModo =
        "historico";


    mdfrProcesoId =
        Number(
            selector.value
        );


    await cargarMdfrProcess();
}


// =========================================================
// PROCESO ACTIVO
// =========================================================

async function mostrarMdfrActivo() {

    mdfrModo =
        "activo";


    mdfrProcesoId =
        null;


    await cargarMdfrProcess();
}


// =========================================================
// CARGAR MDFR PROCESS
// =========================================================

async function cargarMdfrProcess() {

    const estado =
        document.getElementById(
            "mdfrProcessEstado"
        );


    const origen =
        document.getElementById(
            "mdfrOrigen"
        );


    try {

        let url;


        if (
            mdfrModo ===
            "historico"
            &&
            mdfrProcesoId !==
            null
        ) {

            url =
                `/api/procesos/${mdfrProcesoId}/ciclos`;

        }

        else {

            url =
                "/api/proceso/ciclos?modo=activo";
        }


        const response =
            await fetch(
                url,
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(
                data.detail ||
                "Error consultando MDFR-PROCESS."
            );
        }


        if (
            !data.proceso
        ) {

            if (
                estado
            ) {

                estado.innerText =
                    "SIN PROCESO";


                estado.className =
                    "process-badge";
            }


            if (
                origen
            ) {

                origen.innerText =
                    (
                        mdfrModo ===
                        "historico"
                    )
                        ?
                        "No existe el proceso histórico seleccionado."
                        :
                        "No existe un proceso activo.";
            }


            actualizarResumenMdfr(
                null,
                []
            );


            actualizarTablaMdfr(
                []
            );


            dibujarDuracionesMdfr(
                []
            );


            dibujarIntervalosMdfr(
                []
            );


            dibujarCO2Mdfr(
                []
            );


            return;
        }


        if (
            estado
        ) {

            if (
                mdfrModo ===
                "historico"
            ) {

                estado.innerText =
                    `HISTÓRICO ${data.proceso.id}`;

            }

            else {

                estado.innerText =
                    `PROCESO ${data.proceso.id}`;
            }


            estado.className =
                "process-badge active";
        }


        if (
            origen
        ) {

            if (
                mdfrModo ===
                "historico"
            ) {

                origen.innerText =
                    "Proceso histórico"
                    +
                    " | ID "
                    +
                    data.proceso.id
                    +
                    " | Lote "
                    +
                    (
                        data.proceso.lote ||
                        "--"
                    )
                    +
                    " | Estado "
                    +
                    (
                        data.proceso.estado ||
                        "--"
                    );

            }

            else {

                origen.innerText =
                    "Proceso activo"
                    +
                    " | ID "
                    +
                    data.proceso.id
                    +
                    " | Lote "
                    +
                    (
                        data.proceso.lote ||
                        "--"
                    );
            }
        }


        const ciclos =
            (
                data.ciclos ||
                []
            )
            .filter(
                ciclo =>
                    ciclo.estado ===
                    "CERRADO"
            );


        actualizarResumenMdfr(
            data.resumen,
            ciclos
        );


        actualizarTablaMdfr(
            ciclos
        );


        dibujarDuracionesMdfr(
            ciclos
        );


        dibujarIntervalosMdfr(
            ciclos
        );


        dibujarCO2Mdfr(
            ciclos
        );

    }

    catch (
        error
    ) {

        console.error(
            "Error MDFR-PROCESS:",
            error
        );


        if (
            estado
        ) {

            estado.innerText =
                "ERROR";


            estado.className =
                "process-badge";
        }


        if (
            origen
        ) {

            origen.innerText =
                "Error consultando MDFR-PROCESS: "
                +
                error.message;
        }
    }
}


// =========================================================
// RESUMEN MDFR
// =========================================================

function actualizarResumenMdfr(
    resumen,
    ciclos
) {

    resumen =
        resumen ||
        {};


    ciclos =
        Array.isArray(
            ciclos
        )
            ?
            ciclos
            :
            [];


    const campoCiclos =
        document.getElementById(
            "mdfrCiclos"
        );


    const campoLowHigh =
        document.getElementById(
            "mdfrLowHigh"
        );


    const campoPurga =
        document.getElementById(
            "mdfrPurga"
        );


    const campoIntervalo =
        document.getElementById(
            "mdfrIntervalo"
        );


    const campoUltimo =
        document.getElementById(
            "mdfrUltimoIntervalo"
        );


    if (
        campoCiclos
    ) {

        campoCiclos.innerText =
            resumen.ciclos !==
            undefined
                ?
                resumen.ciclos
                :
                ciclos.length;
    }


    if (
        campoLowHigh
    ) {

        campoLowHigh.innerText =
            formatoDuracion(
                resumen
                    .low_high_promedio_s
            );
    }


    if (
        campoPurga
    ) {

        campoPurga.innerText =
            formatoDuracion(
                resumen
                    .purga_promedio_s
            );
    }


    if (
        campoIntervalo
    ) {

        campoIntervalo.innerText =
            formatoDuracion(
                resumen
                    .intervalo_promedio_s
            );
    }


    let ultimo =
        resumen
            .ultimo_intervalo_s;


    if (
        ultimo === null ||
        ultimo === undefined
    ) {

        const intervalos =
            ciclos
            .map(
                ciclo =>
                    ciclo
                        .intervalo_purgas_segundos
            )
            .filter(
                valor =>
                    valor !== null
                    &&
                    valor !== undefined
                    &&
                    Number.isFinite(
                        Number(
                            valor
                        )
                    )
            );


        if (
            intervalos.length >
            0
        ) {

            ultimo =
                intervalos[
                    intervalos.length -
                    1
                ];
        }
    }


    if (
        campoUltimo
    ) {

        campoUltimo.innerText =
            formatoDuracion(
                ultimo
            );
    }
}


// =========================================================
// TABLA MDFR
// =========================================================

function actualizarTablaMdfr(
    ciclos
) {

    const cuerpo =
        document.getElementById(
            "tablaMdfrProcess"
        );


    if (
        !cuerpo
    ) {

        return;
    }


    cuerpo.innerHTML =
        "";


    if (
        !ciclos ||
        ciclos.length ===
        0
    ) {

        cuerpo.innerHTML =
            `
            <tr>
                <td colspan="6">
                    No hay ciclos completos.
                </td>
            </tr>
            `;


        return;
    }


    ciclos.forEach(
        ciclo => {

            const fila =
                document.createElement(
                    "tr"
                );


            fila.innerHTML =
                `
                <td>
                    ${ciclo.numero_ciclo ?? "--"}
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
                    ${
                        ciclo.co2_purge_start_ppm !== null
                        &&
                        ciclo.co2_purge_start_ppm !== undefined
                            ?
                            Number(
                                ciclo.co2_purge_start_ppm
                            ).toFixed(
                                0
                            )
                            +
                            " ppm"
                            :
                            "--"
                    }
                </td>

                <td>
                    ${
                        ciclo.co2_purge_end_ppm !== null
                        &&
                        ciclo.co2_purge_end_ppm !== undefined
                            ?
                            Number(
                                ciclo.co2_purge_end_ppm
                            ).toFixed(
                                0
                            )
                            +
                            " ppm"
                            :
                            "--"
                    }
                </td>
                `;


            cuerpo.appendChild(
                fila
            );
        }
    );
}


// =========================================================
// CANVAS
// =========================================================

function prepararCanvas(
    idCanvas
) {

    const canvas =
        document.getElementById(
            idCanvas
        );


    if (
        !canvas
    ) {

        return null;
    }


    const ctx =
        canvas.getContext(
            "2d"
        );


    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.strokeStyle =
        "#94a3b8";


    ctx.font =
        "13px Arial";


    return {
        canvas,
        ctx
    };
}


// =========================================================
// EJES
// =========================================================

function dibujarEjesBarras(
    ctx,
    W,
    H,
    maximo,
    unidad
) {

    const izquierda =
        70;


    const derecha =
        30;


    const arriba =
        35;


    const abajo =
        55;


    const ancho =
        W -
        izquierda -
        derecha;


    const alto =
        H -
        arriba -
        abajo;


    ctx.beginPath();


    ctx.moveTo(
        izquierda,
        arriba
    );


    ctx.lineTo(
        izquierda,
        H -
        abajo
    );


    ctx.lineTo(
        W -
        derecha,
        H -
        abajo
    );


    ctx.stroke();


    for (
        let i = 0;
        i <= 5;
        i++
    ) {

        const valor =
            maximo *
            (
                1 -
                i /
                5
            );


        const y =
            arriba +
            (
                alto *
                i /
                5
            );


        ctx.beginPath();


        ctx.moveTo(
            izquierda,
            y
        );


        ctx.lineTo(
            W -
            derecha,
            y
        );


        ctx.stroke();


        ctx.fillText(
            valor.toFixed(
                1
            ),
            8,
            y +
            4
        );
    }


    ctx.fillText(
        unidad,
        8,
        20
    );


    return {
        izquierda,
        derecha,
        arriba,
        abajo,
        ancho,
        alto
    };
}


// =========================================================
// GRÁFICA DURACIONES
// =========================================================

function dibujarDuracionesMdfr(
    ciclos
) {

    const preparado =
        prepararCanvas(
            "graficaMdfrDuraciones"
        );


    if (
        !preparado
    ) {

        return;
    }


    const {
        canvas,
        ctx
    } =
        preparado;


    if (
        !ciclos ||
        ciclos.length ===
        0
    ) {

        ctx.fillText(
            "No hay ciclos completos.",
            40,
            60
        );


        return;
    }


    const valores =
        [];


    ciclos.forEach(
        ciclo => {

            valores.push(
                segundosAHoras(
                    ciclo
                        .duracion_segundos
                )
                ||
                0
            );


            valores.push(
                segundosAHoras(
                    ciclo
                        .purga_duracion_segundos
                )
                ||
                0
            );
        }
    );


    const maximo =
        Math.max(
            ...valores,
            1
        )
        *
        1.15;


    const eje =
        dibujarEjesBarras(
            ctx,
            canvas.width,
            canvas.height,
            maximo,
            "horas"
        );


    const grupo =
        eje.ancho /
        ciclos.length;


    ciclos.forEach(
        (
            ciclo,
            indice
        ) => {

            const lowHigh =
                segundosAHoras(
                    ciclo
                        .duracion_segundos
                )
                ||
                0;


            const purga =
                segundosAHoras(
                    ciclo
                        .purga_duracion_segundos
                )
                ||
                0;


            const anchoBarra =
                Math.min(
                    34,
                    grupo *
                    0.25
                );


            const centroX =
                eje.izquierda +
                grupo *
                (
                    indice +
                    0.5
                );


            const alturaLow =
                (
                    lowHigh /
                    maximo
                )
                *
                eje.alto;


            const alturaPurga =
                (
                    purga /
                    maximo
                )
                *
                eje.alto;


            ctx.fillStyle =
                "#2563eb";


            ctx.fillRect(
                centroX -
                anchoBarra -
                3,
                canvas.height -
                eje.abajo -
                alturaLow,
                anchoBarra,
                alturaLow
            );


            ctx.fillStyle =
                "#f59e0b";


            ctx.fillRect(
                centroX +
                3,
                canvas.height -
                eje.abajo -
                alturaPurga,
                anchoBarra,
                alturaPurga
            );


            ctx.fillStyle =
                "#1e293b";


            ctx.fillText(
                `C${ciclo.numero_ciclo}`,
                centroX -
                10,
                canvas.height -
                28
            );
        }
    );


    ctx.fillStyle =
        "#2563eb";


    ctx.fillRect(
        85,
        12,
        14,
        14
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.fillText(
        "LOW → HIGH",
        105,
        24
    );


    ctx.fillStyle =
        "#f59e0b";


    ctx.fillRect(
        205,
        12,
        14,
        14
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.fillText(
        "Purga",
        225,
        24
    );
}


// =========================================================
// GRÁFICA INTERVALOS
// =========================================================

function dibujarIntervalosMdfr(
    ciclos
) {

    const preparado =
        prepararCanvas(
            "graficaMdfrIntervalos"
        );


    if (
        !preparado
    ) {

        return;
    }


    const {
        canvas,
        ctx
    } =
        preparado;


    const datos =
        ciclos.filter(
            ciclo =>
                ciclo
                    .intervalo_purgas_segundos
                !== null
                &&
                ciclo
                    .intervalo_purgas_segundos
                !== undefined
        );


    if (
        datos.length ===
        0
    ) {

        ctx.fillText(
            "No hay intervalos disponibles.",
            40,
            60
        );


        return;
    }


    const valores =
        datos.map(
            ciclo =>
                segundosAHoras(
                    ciclo
                        .intervalo_purgas_segundos
                )
                ||
                0
        );


    const maximo =
        Math.max(
            ...valores,
            1
        )
        *
        1.15;


    const eje =
        dibujarEjesBarras(
            ctx,
            canvas.width,
            canvas.height,
            maximo,
            "horas"
        );


    const grupo =
        eje.ancho /
        datos.length;


    datos.forEach(
        (
            ciclo,
            indice
        ) => {

            const valor =
                segundosAHoras(
                    ciclo
                        .intervalo_purgas_segundos
                )
                ||
                0;


            const altura =
                (
                    valor /
                    maximo
                )
                *
                eje.alto;


            const anchoBarra =
                Math.min(
                    55,
                    grupo *
                    0.45
                );


            const x =
                eje.izquierda +
                grupo *
                (
                    indice +
                    0.5
                )
                -
                anchoBarra /
                2;


            ctx.fillStyle =
                "#7c3aed";


            ctx.fillRect(
                x,
                canvas.height -
                eje.abajo -
                altura,
                anchoBarra,
                altura
            );


            ctx.fillStyle =
                "#1e293b";


            ctx.fillText(
                `C${ciclo.numero_ciclo}`,
                x +
                anchoBarra /
                2 -
                10,
                canvas.height -
                28
            );


            ctx.fillText(
                formatoDuracion(
                    ciclo
                        .intervalo_purgas_segundos
                ),
                x -
                4,
                canvas.height -
                eje.abajo -
                altura -
                8
            );
        }
    );
}


// =========================================================
// GRÁFICA CO2
// =========================================================

function dibujarCO2Mdfr(
    ciclos
) {

    const preparado =
        prepararCanvas(
            "graficaMdfrCO2"
        );


    if (
        !preparado
    ) {

        return;
    }


    const {
        canvas,
        ctx
    } =
        preparado;


    if (
        !ciclos ||
        ciclos.length ===
        0
    ) {

        ctx.fillText(
            "No hay ciclos completos.",
            40,
            60
        );


        return;
    }


    const valores =
        [];


    ciclos.forEach(
        ciclo => {

            valores.push(
                Number(
                    ciclo
                        .co2_purge_start_ppm
                )
                ||
                0
            );


            valores.push(
                Number(
                    ciclo
                        .co2_purge_end_ppm
                )
                ||
                0
            );
        }
    );


    const maximo =
        Math.max(
            ...valores,
            1000
        )
        *
        1.10;


    const eje =
        dibujarEjesBarras(
            ctx,
            canvas.width,
            canvas.height,
            maximo,
            "ppm"
        );


    const grupo =
        eje.ancho /
        ciclos.length;


    ciclos.forEach(
        (
            ciclo,
            indice
        ) => {

            const inicio =
                Number(
                    ciclo
                        .co2_purge_start_ppm
                )
                ||
                0;


            const fin =
                Number(
                    ciclo
                        .co2_purge_end_ppm
                )
                ||
                0;


            const anchoBarra =
                Math.min(
                    34,
                    grupo *
                    0.25
                );


            const centroX =
                eje.izquierda +
                grupo *
                (
                    indice +
                    0.5
                );


            const alturaInicio =
                (
                    inicio /
                    maximo
                )
                *
                eje.alto;


            const alturaFin =
                (
                    fin /
                    maximo
                )
                *
                eje.alto;


            ctx.fillStyle =
                "#dc2626";


            ctx.fillRect(
                centroX -
                anchoBarra -
                3,
                canvas.height -
                eje.abajo -
                alturaInicio,
                anchoBarra,
                alturaInicio
            );


            ctx.fillStyle =
                "#16a34a";


            ctx.fillRect(
                centroX +
                3,
                canvas.height -
                eje.abajo -
                alturaFin,
                anchoBarra,
                alturaFin
            );


            ctx.fillStyle =
                "#1e293b";


            ctx.fillText(
                `C${ciclo.numero_ciclo}`,
                centroX -
                10,
                canvas.height -
                28
            );
        }
    );


    ctx.fillStyle =
        "#dc2626";


    ctx.fillRect(
        85,
        12,
        14,
        14
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.fillText(
        "Inicio purga",
        105,
        24
    );


    ctx.fillStyle =
        "#16a34a";


    ctx.fillRect(
        220,
        12,
        14,
        14
    );


    ctx.fillStyle =
        "#1e293b";


    ctx.fillText(
        "Fin purga",
        240,
        24
    );
}


// =========================================================
// INICIO
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    async function() {

        configurarInicial();


        await cargarProcesosMdfr();


        await cargarMdfrProcess();
    }
);


// =========================================================
// ACTUALIZACIONES
// =========================================================

// Lista de procesos

setInterval(
    cargarProcesosMdfr,
    60000
);


// MDFR PROCESS
//
// Si el usuario está viendo histórico,
// mantiene el mismo proceso seleccionado.

setInterval(
    cargarMdfrProcess,
    30000
);