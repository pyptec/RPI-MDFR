// =========================================================
// VARIABLE HISTÓRICA ACTUAL
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
        horaHasta - 2;


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
        ) * 10;


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
// FECHA HORA DEL FILTRO
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
// FORMATO FECHA COLOMBIA
// =========================================================

function formatoColombia(
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
// FORMATO HORA
// =========================================================

function formatoHoraColombia(
    timestamp
) {

    const fecha =
        new Date(
            timestamp
        );


    return fecha.toLocaleTimeString(
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
// FORMATO DURACIÓN
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
// SEGUNDOS A HORAS DECIMALES
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
// SELECCIÓN VARIABLE
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
// BOTONES DE VARIABLES
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
// RESULTADO HISTÓRICO
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


    if (
        !datos ||
        datos.length === 0
    ) {

        ctx.font =
            "18px Arial";


        ctx.fillText(
            "No hay datos para este período.",
            40,
            60
        );


        activarTooltip(
            canvas,
            [],
            unidad
        );


        return;
    }


    const valores =
        datos
        .map(
            d =>
                Number(
                    d.valor
                )
        )
        .filter(
            v =>
                Number.isFinite(
                    v
                )
        );


    if (
        valores.length === 0
    ) {

        ctx.font =
            "18px Arial";


        ctx.fillText(
            "No hay valores numéricos válidos.",
            40,
            60
        );


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


    let margenValor =
        (
            maximoReal -
            minimoReal
        ) *
        0.10;


    if (
        margenValor === 0
    ) {

        margenValor =
            Math.abs(
                maximoReal
            ) *
            0.05;


        if (
            margenValor === 0
        ) {

            margenValor =
                1;
        }
    }


    const minimo =
        minimoReal -
        margenValor;


    const maximo =
        maximoReal +
        margenValor;


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


    ctx.font =
        "14px Arial";


    ctx.fillText(
        `${titulo} (${unidad})`,
        margenIzq,
        25
    );


    // =====================================================
    // EJES
    // =====================================================

    ctx.beginPath();


    ctx.moveTo(
        margenIzq,
        margenSup
    );


    ctx.lineTo(
        margenIzq,
        H - margenInf
    );


    ctx.lineTo(
        W - margenDer,
        H - margenInf
    );


    ctx.stroke();


    // =====================================================
    // ESCALA Y
    // =====================================================

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
            W - margenDer,
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


    // =====================================================
    // PUNTOS
    // =====================================================

    const puntos =
        [];


    datos.forEach(
        (
            dato,
            i
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
                    i /
                    Math.max(
                        datos.length - 1,
                        1
                    )
                ) *
                ancho;


            const y =
                margenSup +
                (
                    1 -
                    (
                        valor -
                        minimo
                    ) /
                    rango
                ) *
                alto;


            puntos.push({
                x,
                y,
                dato
            });
        }
    );


    // =====================================================
    // LÍNEA
    // =====================================================

    if (
        puntos.length > 0
    ) {

        ctx.beginPath();


        puntos.forEach(
            (
                punto,
                i
            ) => {

                if (
                    i === 0
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


    // =====================================================
    // PUNTOS
    // =====================================================

    puntos.forEach(
        punto => {

            ctx.beginPath();


            ctx.arc(
                punto.x,
                punto.y,
                4,
                0,
                Math.PI * 2
            );


            ctx.fill();
        }
    );


    // =====================================================
    // ETIQUETAS X
    // =====================================================

    const cantidadEtiquetas =
        Math.min(
            6,
            datos.length
        );


    for (
        let i = 0;
        i < cantidadEtiquetas;
        i++
    ) {

        const indice =
            Math.round(
                i *
                (
                    datos.length - 1
                ) /
                Math.max(
                    cantidadEtiquetas - 1,
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
                    datos.length - 1,
                    1
                )
            ) *
            ancho;


        const hora =
            formatoHoraColombia(
                dato.timestamp
            );


        ctx.fillText(
            hora,
            x - 20,
            H - 45
        );
    }


    // =====================================================
    // FECHA INICIO / FIN
    // =====================================================

    const primeraFecha =
        formatoColombia(
            datos[0]
                .timestamp
        );


    const ultimaFecha =
        formatoColombia(
            datos[
                datos.length - 1
            ].timestamp
        );


    ctx.fillText(
        primeraFecha,
        margenIzq,
        H - 15
    );


    ctx.fillText(
        ultimaFecha,
        W - 240,
        H - 15
    );


    activarTooltip(
        canvas,
        puntos,
        unidad
    );
}


// =========================================================
// TOOLTIP HISTÓRICO
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


            if (
                !puntos ||
                puntos.length === 0
            ) {

                tooltip.style.display =
                    "none";

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
                ) *
                escalaX;


            const mouseY =
                (
                    event.clientY -
                    rect.top
                ) *
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
                            dx * dx +
                            dy * dy
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
// MDFR PROCESS
// =========================================================

async function cargarMdfrProcess() {

    const estado =
        document.getElementById(
            "mdfrProcessEstado"
        );


    try {

        const response =
            await fetch(
                "/api/proceso/ciclos?modo=activo",
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


        // =================================================
        // SIN PROCESO
        // =================================================

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


            actualizarResumenMdfr(
                null
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


        // =================================================
        // PROCESO ACTIVO
        // =================================================

        if (
            estado
        ) {

            estado.innerText =
                `PROCESO ${data.proceso.id}`;


            estado.className =
                "process-badge active";
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
            data.resumen
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
    }
}


// =========================================================
// RESUMEN MDFR
// =========================================================

function actualizarResumenMdfr(
    resumen
) {

    const ciclos =
        document.getElementById(
            "mdfrCiclos"
        );


    const lowHigh =
        document.getElementById(
            "mdfrLowHigh"
        );


    const purga =
        document.getElementById(
            "mdfrPurga"
        );


    const intervalo =
        document.getElementById(
            "mdfrIntervalo"
        );


    if (
        !resumen
    ) {

        if (ciclos) {
            ciclos.innerText =
                "--";
        }


        if (lowHigh) {
            lowHigh.innerText =
                "--";
        }


        if (purga) {
            purga.innerText =
                "--";
        }


        if (intervalo) {
            intervalo.innerText =
                "--";
        }


        return;
    }


    if (
        ciclos
    ) {

        ciclos.innerText =
            resumen.ciclos ??
            0;
    }


    if (
        lowHigh
    ) {

        lowHigh.innerText =
            formatoDuracion(
                resumen
                    .low_high_promedio_s
            );
    }


    if (
        purga
    ) {

        purga.innerText =
            formatoDuracion(
                resumen
                    .purga_promedio_s
            );
    }


    if (
        intervalo
    ) {

        intervalo.innerText =
            formatoDuracion(
                resumen
                    .intervalo_promedio_s
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
        ciclos.length === 0
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
                            ).toFixed(0)
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
                            ).toFixed(0)
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
// UTILIDAD CANVAS MDFR
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


    ctx.font =
        "13px Arial";


    return {
        canvas,
        ctx
    };
}


// =========================================================
// EJE GRÁFICA BARRAS
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
        H - abajo
    );


    ctx.lineTo(
        W - derecha,
        H - abajo
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
                i / 5
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
            W - derecha,
            y
        );


        ctx.stroke();


        ctx.fillText(
            valor.toFixed(
                1
            ),
            8,
            y + 4
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
// GRÁFICA 1 - LOW HIGH Y PURGA
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
        ciclos.length === 0
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
                ) || 0
            );


            valores.push(
                segundosAHoras(
                    ciclo
                        .purga_duracion_segundos
                ) || 0
            );
        }
    );


    const maximo =
        Math.max(
            ...valores,
            1
        ) *
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
                ) || 0;


            const purga =
                segundosAHoras(
                    ciclo
                        .purga_duracion_segundos
                ) || 0;


            const anchoBarra =
                Math.min(
                    34,
                    grupo * 0.25
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
                ) *
                eje.alto;


            const alturaPurga =
                (
                    purga /
                    maximo
                ) *
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
                centroX - 10,
                canvas.height - 28
            );
        }
    );


    // LEYENDA

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
// GRÁFICA 2 - INTERVALOS
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
        datos.length === 0
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
                ) || 0
        );


    const maximo =
        Math.max(
            ...valores,
            1
        ) *
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
                ) || 0;


            const altura =
                (
                    valor /
                    maximo
                ) *
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
                x - 4,
                canvas.height -
                eje.abajo -
                altura -
                8
            );
        }
    );
}


// =========================================================
// GRÁFICA 3 - CO2 PURGA
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
        ciclos.length === 0
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
                ) || 0
            );


            valores.push(
                Number(
                    ciclo
                        .co2_purge_end_ppm
                ) || 0
            );
        }
    );


    const maximo =
        Math.max(
            ...valores,
            1000
        ) *
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
                ) || 0;


            const fin =
                Number(
                    ciclo
                        .co2_purge_end_ppm
                ) || 0;


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
                ) *
                eje.alto;


            const alturaFin =
                (
                    fin /
                    maximo
                ) *
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


    // LEYENDA

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
    function() {

        configurarInicial();

        cargarMdfrProcess();
    }
);