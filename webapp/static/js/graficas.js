function cargarHoras() {

    const desde = document.getElementById("horaDesde");
    const hasta = document.getElementById("horaHasta");

    for (let h = 0; h < 24; h++) {

        const texto = String(h).padStart(
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

    document.getElementById(
        "fechaDesde"
    ).value = hoy;

    document.getElementById(
        "fechaHasta"
    ).value = hoy;

    const ahora = new Date();

    let horaActual = ahora.getHours();

    let horaAnterior = horaActual - 1;

    if (horaAnterior < 0) {
        horaAnterior = 0;
    }

    document.getElementById(
        "horaDesde"
    ).value = String(
        horaAnterior
    ).padStart(2, "0");

    document.getElementById(
        "horaHasta"
    ).value = String(
        horaActual
    ).padStart(2, "0");


    const minuto = Math.floor(
        ahora.getMinutes() / 10
    ) * 10;

    document.getElementById(
        "minHasta"
    ).value = String(
        minuto
    ).padStart(2, "0");

    document.getElementById(
        "minDesde"
    ).value = String(
        minuto
    ).padStart(2, "0");
}


function obtenerFechaHora(
    prefijo
) {

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


async function consultarCO2() {

    const desde = obtenerFechaHora(
        "Desde"
    );

    const hasta = obtenerFechaHora(
        "Hasta"
    );


    const url =
        "/api/historico" +
        "?sensor=CT01CO2" +
        "&variable=co2" +
        `&desde=${encodeURIComponent(desde)}` +
        `&hasta=${encodeURIComponent(hasta)}`;


    const resultado = document.getElementById(
        "resultado"
    );


    resultado.innerHTML =
        "Consultando...";


    try {

        const response = await fetch(
            url
        );

        const data = await response.json();


        if (!response.ok) {

            resultado.innerHTML =
                data.detail || "Error consultando datos.";

            return;
        }


        resultado.innerHTML =
            `${data.cantidad} mediciones encontradas`;

        dibujarGrafica(
            data.datos
        );

    }

    catch (error) {

        resultado.innerHTML =
            "Error comunicándose con el servidor.";

        console.error(
            error
        );
    }
}


function dibujarGrafica(datos) {

    const canvas = document.getElementById(
        "graficaCO2"
    );

    const ctx = canvas.getContext(
        "2d"
    );


    const W = canvas.width;
    const H = canvas.height;


    ctx.clearRect(
        0,
        0,
        W,
        H
    );


    if (!datos || datos.length === 0) {

        ctx.font = "18px Arial";

        ctx.fillText(
            "No hay datos para este período.",
            40,
            60
        );

        return;
    }


    const valores = datos.map(
        d => Number(d.valor)
    );


    const minimo = Math.min(
        ...valores
    );

    const maximo = Math.max(
        ...valores
    );


    const margenIzq = 70;
    const margenDer = 30;
    const margenSup = 30;
    const margenInf = 60;


    const ancho =
        W -
        margenIzq -
        margenDer;


    const alto =
        H -
        margenSup -
        margenInf;


    // Ejes

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


    let rango = maximo - minimo;

    if (rango === 0) {
        rango = 1;
    }


    // Línea CO2

    ctx.beginPath();


    datos.forEach(
        (dato, i) => {

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
                        Number(dato.valor) -
                        minimo
                    ) /
                    rango
                ) *
                alto;


            if (i === 0) {

                ctx.moveTo(
                    x,
                    y
                );

            }

            else {

                ctx.lineTo(
                    x,
                    y
                );

            }
        }
    );


    ctx.stroke();


    // Escalas verticales

    ctx.font = "13px Arial";


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
            alto *
            i /
            5;


        ctx.fillText(
            valor.toFixed(0),
            10,
            y + 4
        );
    }


    // Primera fecha

    const primero = new Date(
        datos[0].timestamp
    );


    const ultimo = new Date(
        datos[
            datos.length - 1
        ].timestamp
    );


    ctx.fillText(
        formatoColombia(
            datos[0].timestamp
        ),
        margenIzq,
        H - 20
    );


    ctx.fillText(
        formatoColombia(
            datos[datos.length - 1].timestamp
        ),
        W - 210,
        H - 20
    );
}


document.addEventListener(
    "DOMContentLoaded",
    configurarInicial
);

function formatoColombia(timestamp) {

    const fecha = new Date(timestamp);

    return fecha.toLocaleString(
        "es-CO",
        {
            timeZone: "America/Bogota",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        }
    );
}