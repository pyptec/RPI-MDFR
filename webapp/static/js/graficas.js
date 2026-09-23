let variableActual = {
    sensor: "CT01CO2",
    variable: "co2",
    titulo: "CO₂",
    unidad: "ppm"
};


function cargarHoras() {

    const desde = document.getElementById("horaDesde");
    const hasta = document.getElementById("horaHasta");

    desde.innerHTML = "";
    hasta.innerHTML = "";

    for (let h = 0; h < 24; h++) {

        const texto = String(h).padStart(2, "0");

        desde.add(new Option(texto, texto));
        hasta.add(new Option(texto, texto));
    }
}


function fechaHoy() {

    const ahora = new Date();

    const year = ahora.getFullYear();

    const month = String(
        ahora.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        ahora.getDate()
    ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function configurarInicial() {

    cargarHoras();

    const hoy = fechaHoy();

    document.getElementById("fechaDesde").value = hoy;
    document.getElementById("fechaHasta").value = hoy;

    const ahora = new Date();

    let horaHasta = ahora.getHours();
    let horaDesde = horaHasta - 2;

    if (horaDesde < 0) {
        horaDesde = 0;
    }

    document.getElementById(
        "horaDesde"
    ).value = String(
        horaDesde
    ).padStart(2, "0");

    document.getElementById(
        "horaHasta"
    ).value = String(
        horaHasta
    ).padStart(2, "0");

    const minuto = Math.floor(
        ahora.getMinutes() / 10
    ) * 10;

    document.getElementById(
        "minDesde"
    ).value = String(
        minuto
    ).padStart(2, "0");

    document.getElementById(
        "minHasta"
    ).value = String(
        minuto
    ).padStart(2, "0");
}


function obtenerFechaHora(prefijo) {

    const fecha = document.getElementById(
        `fecha${prefijo}`
    ).value;

    const hora = document.getElementById(
        `hora${prefijo}`
    ).value;

    const minuto = document.getElementById(
        `min${prefijo}`
    ).value;

    return `${fecha}T${hora}:${minuto}`;
}


function formatoColombia(timestamp) {

    const fecha = new Date(timestamp);

    return fecha.toLocaleString(
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


function formatoHoraColombia(timestamp) {

    const fecha = new Date(timestamp);

    return fecha.toLocaleTimeString(
        "es-CO",
        {
            timeZone: "America/Bogota",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        }
    );
}


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

    if (tituloGrafica) {
        tituloGrafica.innerText = titulo;
    }

    consultarHistorico();
}


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


async function consultarHistorico() {

    const desde = obtenerFechaHora(
        "Desde"
    );

    const hasta = obtenerFechaHora(
        "Hasta"
    );

    if (!desde || !hasta) {

        mostrarResultado(
            "Seleccione el rango de fechas."
        );

        return;
    }

    const url =
        "/api/historico" +
        `?sensor=${encodeURIComponent(
            variableActual.sensor
        )}` +
        `&variable=${encodeURIComponent(
            variableActual.variable
        )}` +
        `&desde=${encodeURIComponent(
            desde
        )}` +
        `&hasta=${encodeURIComponent(
            hasta
        )}`;

    mostrarResultado(
        "Consultando..."
    );

    try {

        const response =
            await fetch(url);

        const data =
            await response.json();

        if (!response.ok) {

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

    } catch (error) {

        console.error(error);

        mostrarResultado(
            "Error comunicándose con el servidor."
        );

        limpiarGrafica();
    }
}


function mostrarResultado(texto) {

    const resultado =
        document.getElementById(
            "resultado"
        );

    if (resultado) {
        resultado.innerHTML = texto;
    }
}


function limpiarGrafica() {

    const canvas =
        document.getElementById(
            "graficaCO2"
        );

    if (!canvas) {
        return;
    }

    const ctx =
        canvas.getContext("2d");

    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );
}


function dibujarGrafica(
    datos,
    titulo,
    unidad
) {

    const canvas =
        document.getElementById(
            "graficaCO2"
        );

    if (!canvas) {
        return;
    }

    const ctx =
        canvas.getContext("2d");

    const W = canvas.width;
    const H = canvas.height;

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

        ctx.font = "18px Arial";

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

    const valores = datos
        .map(d => Number(d.valor))
        .filter(v => Number.isFinite(v));

    if (valores.length === 0) {

        ctx.font = "18px Arial";

        ctx.fillText(
            "No hay valores numéricos válidos.",
            40,
            60
        );

        return;
    }

    const minimoReal =
        Math.min(...valores);

    const maximoReal =
        Math.max(...valores);

    let margenValor =
        (maximoReal - minimoReal) *
        0.10;

    if (margenValor === 0) {

        margenValor =
            Math.abs(
                maximoReal
            ) * 0.05;

        if (margenValor === 0) {
            margenValor = 1;
        }
    }

    const minimo =
        minimoReal - margenValor;

    const maximo =
        maximoReal + margenValor;

    const margenIzq = 75;
    const margenDer = 40;
    const margenSup = 45;
    const margenInf = 80;

    const ancho =
        W -
        margenIzq -
        margenDer;

    const alto =
        H -
        margenSup -
        margenInf;

    const rango =
        maximo - minimo;

    ctx.font = "14px Arial";

    ctx.fillText(
        `${titulo} (${unidad})`,
        margenIzq,
        25
    );


    // ============================
    // EJES
    // ============================

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


    // ============================
    // ESCALA Y
    // ============================

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
                unidad === "ppm"
                    ? 0
                    : 1
            ),
            8,
            y + 4
        );
    }


    // ============================
    // PUNTOS
    // ============================

    const puntos = [];

    datos.forEach(
        (dato, i) => {

            const valor =
                Number(dato.valor);

            if (
                !Number.isFinite(valor)
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


    // ============================
    // LÍNEA
    // ============================

    if (puntos.length > 0) {

        ctx.beginPath();

        puntos.forEach(
            (punto, i) => {

                if (i === 0) {

                    ctx.moveTo(
                        punto.x,
                        punto.y
                    );

                } else {

                    ctx.lineTo(
                        punto.x,
                        punto.y
                    );
                }
            }
        );

        ctx.stroke();
    }


    // ============================
    // CÍRCULOS DE MEDICIÓN
    // ============================

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


    // ============================
    // ETIQUETAS EJE X
    // ============================

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
            datos[indice];

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


    // ============================
    // FECHA INICIO / FIN
    // ============================

    const primeraFecha =
        formatoColombia(
            datos[0].timestamp
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


function activarTooltip(
    canvas,
    puntos,
    unidad
) {

    canvas.onmousemove =
        function(event) {

            const tooltip =
                document.getElementById(
                    "tooltipGrafica"
                );

            if (!tooltip) {
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
                canvas.getBoundingClientRect();

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

            let cercano = null;
            let distanciaMinima = 18;

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

            if (!cercano) {

                tooltip.style.display =
                    "none";

                return;
            }

            tooltip.style.display =
                "block";

            tooltip.innerHTML =
                `<strong>${formatoColombia(
                    cercano.dato.timestamp
                )}</strong><br>` +
                `${variableActual.titulo}: ` +
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

            if (tooltip) {

                tooltip.style.display =
                    "none";
            }
        };
}


document.addEventListener(
    "DOMContentLoaded",
    configurarInicial
);