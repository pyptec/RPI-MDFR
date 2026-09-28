function valorNumero(
    valor,
    decimales = 1
) {

    if (
        valor === null ||
        valor === undefined
    ) {
        return "--";
    }

    return Number(
        valor
    ).toFixed(
        decimales
    );
}


async function cargarConfiguracion() {

    try {

        const response =
            await fetch(
                "/api/configuracion",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Error cargando configuración"
            );
        }


        // =============================================
        // CO2
        // =============================================

        document.getElementById(
            "co2Low"
        ).innerText =
            `${data.co2.low ?? "--"} ppm`;


        document.getElementById(
            "co2High"
        ).innerText =
            `${data.co2.high ?? "--"} ppm`;


        document.getElementById(
            "aireFresco"
        ).innerText =
            `${data.co2.aire_fresco_minutos ?? "--"} min`;


        // =============================================
        // HUMEDAD
        // =============================================

        document.getElementById(
            "humedadLow"
        ).innerText =
            `${data.humedad.low ?? "--"} %`;


        document.getElementById(
            "humedadHigh"
        ).innerText =
            `${data.humedad.high ?? "--"} %`;


        // =============================================
        // HVAC
        // =============================================

        document.getElementById(
            "tempTarget"
        ).value =
            valorNumero(
                data.hvac.temp_target
            );


        document.getElementById(
            "tempLow"
        ).value =
            valorNumero(
                data.hvac.temp_low
            );


        document.getElementById(
            "tempHigh"
        ).value =
            valorNumero(
                data.hvac.temp_high
            );


    } catch (error) {

        console.error(
            "Error cargarConfiguracion:",
            error
        );
    }
}


async function guardarTemperaturaHVAC() {

    const estado =
        document.getElementById(
            "estadoGuardarHVAC"
        );


    const boton =
        document.getElementById(
            "btnGuardarTemperatura"
        );


    const tempTarget =
        Number(
            document.getElementById(
                "tempTarget"
            ).value
        );


    const tempLow =
        Number(
            document.getElementById(
                "tempLow"
            ).value
        );


    const tempHigh =
        Number(
            document.getElementById(
                "tempHigh"
            ).value
        );


    if (
        !Number.isFinite(
            tempTarget
        ) ||
        !Number.isFinite(
            tempLow
        ) ||
        !Number.isFinite(
            tempHigh
        )
    ) {

        estado.innerText =
            "Valores inválidos.";

        return;
    }


    try {

        boton.disabled =
            true;

        estado.innerText =
            "Guardando...";


        const response =
            await fetch(
                "/api/configuracion/hvac",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            temp_target:
                                tempTarget,

                            temp_low:
                                tempLow,

                            temp_high:
                                tempHigh
                        }
                    )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "No se pudo guardar"
            );
        }


        estado.innerText =
            "Configuración guardada.";


        await cargarConfiguracion();


    } catch (error) {

        console.error(
            error
        );

        estado.innerText =
            error.message;


    } finally {

        boton.disabled =
            false;
    }
}


document.addEventListener(
    "DOMContentLoaded",
    cargarConfiguracion
);