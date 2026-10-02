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
// =========================================================
// CONFIGURACIÓN RED ETHERNET
// =========================================================

function validarIPv4(
    valor
) {

    const partes =
        String(
            valor
        )
        .trim()
        .split(".");


    if (
        partes.length !== 4
    ) {

        return false;
    }


    return partes.every(
        parte => {

            if (
                parte === ""
            ) {

                return false;
            }


            const numero =
                Number(
                    parte
                );


            return (
                Number.isInteger(
                    numero
                )
                &&
                numero >= 0
                &&
                numero <= 255
                &&
                String(
                    numero
                ) ===
                String(
                    Number(
                        parte
                    )
                )
            );
        }
    );
}


// =========================================================
// MOSTRAR NUEVA URL
// =========================================================

function actualizarNuevaUrlRed() {

    const campoIp =
        document.getElementById(
            "redIp"
        );


    const campoUrl =
        document.getElementById(
            "redNuevaUrl"
        );


    if (
        !campoIp ||
        !campoUrl
    ) {

        return;
    }


    const ip =
        campoIp.value.trim();


    if (
        validarIPv4(
            ip
        )
    ) {

        campoUrl.innerText =
            `http://${ip}:8080`;

    }

    else {

        campoUrl.innerText =
            "--";
    }
}


// =========================================================
// CARGAR ESTADO DE RED
// =========================================================

async function cargarConfiguracionRed() {

    try {

        const response =
            await fetch(
                "/api/red/estado",
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
                "Error consultando red."
            );
        }


        const red =
            data.red ||
            {};


        const ipActual =
            document.getElementById(
                "redIpActual"
            );


        const mascaraActual =
            document.getElementById(
                "redMascaraActual"
            );


        const gatewayActual =
            document.getElementById(
                "redGatewayActual"
            );


        const estadoLink =
            document.getElementById(
                "redEstadoLink"
            );


        const campoIp =
            document.getElementById(
                "redIp"
            );


        const campoMascara =
            document.getElementById(
                "redMascara"
            );


        const campoGateway =
            document.getElementById(
                "redGateway"
            );


        if (
            ipActual
        ) {

            ipActual.innerText =
                red.ip ||
                "--";
        }


        if (
            mascaraActual
        ) {

            mascaraActual.innerText =
                red.mascara ||
                "--";
        }


        if (
            gatewayActual
        ) {

            gatewayActual.innerText =
                red.gateway ||
                "--";
        }


        if (
            estadoLink
        ) {

            estadoLink.innerText =
                red.link ||
                "--";
        }


        if (
            campoIp
            &&
            red.ip
        ) {

            campoIp.value =
                red.ip;
        }


        if (
            campoMascara
        ) {

            campoMascara.value =
                red.mascara ||
                "255.255.240.0";
        }


        if (
            campoGateway
            &&
            red.gateway
        ) {

            campoGateway.value =
                red.gateway;
        }


        actualizarNuevaUrlRed();


    }

    catch (
        error
    ) {

        console.error(
            "Error cargarConfiguracionRed:",
            error
        );


        const estado =
            document.getElementById(
                "estadoGuardarRed"
            );


        if (
            estado
        ) {

            estado.innerText =
                error.message;
        }
    }
}


// =========================================================
// GUARDAR CONFIGURACIÓN DE RED
// =========================================================

async function guardarConfiguracionRed() {

    const boton =
        document.getElementById(
            "btnGuardarRed"
        );


    const estado =
        document.getElementById(
            "estadoGuardarRed"
        );


    const ip =
        document.getElementById(
            "redIp"
        )
        .value
        .trim();


    const mascara =
        document.getElementById(
            "redMascara"
        )
        .value
        .trim();


    const gateway =
        document.getElementById(
            "redGateway"
        )
        .value
        .trim();


    // =====================================================
    // VALIDACIÓN LOCAL
    // =====================================================

    if (
        !validarIPv4(
            ip
        )
    ) {

        estado.innerText =
            "Dirección IP inválida.";


        return;
    }


    if (
        !validarIPv4(
            mascara
        )
    ) {

        estado.innerText =
            "Máscara inválida.";


        return;
    }


    if (
        !validarIPv4(
            gateway
        )
    ) {

        estado.innerText =
            "Puerta de enlace inválida.";


        return;
    }


    const nuevaUrl =
        `http://${ip}:8080`;


    const confirmar =
        window.confirm(
            "Se modificará la configuración de eth0.\n\n"
            +
            `IP: ${ip}\n`
            +
            `Máscara: ${mascara}\n`
            +
            `Gateway: ${gateway}\n\n`
            +
            "La conexión web actual puede perderse.\n"
            +
            "Después del cambio deberá ingresar por:\n\n"
            +
            nuevaUrl
            +
            "\n\n"
            +
            "¿Desea continuar?"
        );


    if (
        !confirmar
    ) {

        return;
    }


    try {

        boton.disabled =
            true;


        estado.innerText =
            "Aplicando configuración...";


        const response =
            await fetch(
                "/api/red/configurar",
                {
                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                ip:
                                    ip,

                                mascara:
                                    mascara,

                                gateway:
                                    gateway
                            }
                        )
                }
            );


        let data =
            null;


        try {

            data =
                await response.json();

        }

        catch (
            error
        ) {

            // Es posible que la conexión se corte
            // inmediatamente después de cambiar la IP.
        }


        if (
            !response.ok
        ) {

            throw new Error(
                (
                    data
                    &&
                    data.detail
                )
                    ?
                    data.detail
                    :
                    "No se pudo aplicar la configuración."
            );
        }


        estado.innerText =
            (
                "Configuración aplicada. "
                +
                "Abra "
                +
                nuevaUrl
            );


        setTimeout(
            function() {

                window.location.href =
                    nuevaUrl;

            },
            4000
        );


    }

    catch (
        error
    ) {

        console.error(
            "Error guardarConfiguracionRed:",
            error
        );


        // Si la IP cambió, el navegador puede reportar
        // error aunque NetworkManager sí haya aplicado.
        // Por eso mostramos la nueva URL.

        estado.innerText =
            (
                error.message
                +
                " | Si la IP cambió, pruebe: "
                +
                nuevaUrl
            );


    }

    finally {

        boton.disabled =
            false;
    }
}


// =========================================================
// EVENTOS DE LA PANTALLA DE RED
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        cargarConfiguracionRed();


        const campoIp =
            document.getElementById(
                "redIp"
            );


        if (
            campoIp
        ) {

            campoIp.addEventListener(
                "input",
                actualizarNuevaUrlRed
            );
        }
    }
);