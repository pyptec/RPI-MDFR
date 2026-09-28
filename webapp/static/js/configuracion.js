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
        ).value =
            data.co2.low ?? "";


        document.getElementById(
            "co2High"
        ).value =
            data.co2.high ?? "";


        document.getElementById(
            "aireFresco"
        ).value =
            data.co2.aire_fresco_minutos ?? "";


        // =============================================
        // HUMEDAD
        // =============================================

        document.getElementById(
            "humedadLow"
        ).value =
            data.humedad.low ?? "";


        document.getElementById(
            "humedadHigh"
        ).value =
            data.humedad.high ?? "";
        

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

async function guardarConfiguracionCO2() {

    const boton =
        document.getElementById(
            "btnGuardarCO2"
        );

    const estado =
        document.getElementById(
            "estadoGuardarCO2"
        );

    const low =
        Number(
            document.getElementById(
                "co2Low"
            ).value
        );

    const high =
        Number(
            document.getElementById(
                "co2High"
            ).value
        );

    const aireFresco =
        Number(
            document.getElementById(
                "aireFresco"
            ).value
        );


    if (
        !Number.isFinite(low) ||
        !Number.isFinite(high) ||
        !Number.isFinite(aireFresco)
    ) {

        estado.innerText =
            "Valores inválidos.";

        return;
    }


    if (low >= high) {

        estado.innerText =
            "LOW debe ser menor que HIGH.";

        return;
    }


    try {

        boton.disabled =
            true;

        estado.innerText =
            "Guardando...";


        const response =
            await fetch(
                "/api/configuracion/co2",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            low: low,
                            high: high,
                            aire_fresco_minutos:
                                aireFresco
                        }
                    )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "No se pudo guardar CO₂"
            );
        }


        estado.innerText =
            "Configuración guardada.";

        await cargarConfiguracion();


    } catch (error) {

        estado.innerText =
            error.message;


    } finally {

        boton.disabled =
            false;
    }
}


async function guardarConfiguracionHumedad() {

    const boton =
        document.getElementById(
            "btnGuardarHumedad"
        );

    const estado =
        document.getElementById(
            "estadoGuardarHumedad"
        );

    const low =
        Number(
            document.getElementById(
                "humedadLow"
            ).value
        );

    const high =
        Number(
            document.getElementById(
                "humedadHigh"
            ).value
        );


    if (
        !Number.isFinite(low) ||
        !Number.isFinite(high)
    ) {

        estado.innerText =
            "Valores inválidos.";

        return;
    }


    if (
        low < 0 ||
        high > 100
    ) {

        estado.innerText =
            "La humedad debe estar entre 0 y 100 %.";

        return;
    }


    if (low >= high) {

        estado.innerText =
            "LOW debe ser menor que HIGH.";

        return;
    }


    try {

        boton.disabled =
            true;

        estado.innerText =
            "Guardando...";


        const response =
            await fetch(
                "/api/configuracion/humedad",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            low: low,
                            high: high
                        }
                    )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "No se pudo guardar humedad"
            );
        }


        estado.innerText =
            "Configuración guardada.";

        await cargarConfiguracion();


    } catch (error) {

        estado.innerText =
            error.message;


    } finally {

        boton.disabled =
            false;
    }
}