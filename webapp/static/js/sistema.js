function texto(
    valor,
    defecto = "--"
) {

    if (
        valor === null ||
        valor === undefined
    ) {
        return defecto;
    }

    return String(
        valor
    );
}


function formatoFechaSistema(
    fecha
) {

    if (!fecha) {
        return "--";
    }

    try {

        return new Date(
            fecha
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

                second:
                    "2-digit",

                hour12:
                    false
            }
        );

    } catch (error) {

        return "--";
    }
}


async function cargarSistema() {

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
        // RASPBERRY
        // =============================================

        document.getElementById(
            "cpuTemp"
        ).innerText =
            data.raspberry
                .temperatura_cpu !== null
                ?
                `${data.raspberry.temperatura_cpu} °C`
                :
                "--";


        document.getElementById(
            "cpuUso"
        ).innerText =
            data.raspberry
                .uso_cpu !== null
                ?
                `${data.raspberry.uso_cpu} %`
                :
                "--";


        const ram =
            data.raspberry.ram;


        document.getElementById(
            "ramUso"
        ).innerText =
            ram
                ?
                `${ram.usado_mb} / ${ram.total_mb} MB (${ram.porcentaje} %)`
                :
                "--";


        const disco =
            data.raspberry.disco;


        document.getElementById(
            "discoUso"
        ).innerText =
            disco
                ?
                `${disco.usado_gb} / ${disco.total_gb} GB (${disco.porcentaje} %)`
                :
                "--";


        const uptime =
            data.raspberry.uptime;


        document.getElementById(
            "uptime"
        ).innerText =
            uptime
                ?
                `${uptime.dias} d ${uptime.horas} h ${uptime.minutos} min`
                :
                "--";


        // =============================================
        // RED
        // =============================================

        document.getElementById(
            "ipLocal"
        ).innerText =
            texto(
                data.red.ip
            );


        document.getElementById(
            "hostname"
        ).innerText =
            texto(
                data.red.hostname
            );


        const internetElemento =
            document.getElementById(
                "internetEstado"
            );


        if (
            data.red.internet
        ) {

            internetElemento.innerText =
                "CONECTADO";

            internetElemento.className =
                "config-value estado-activo";

        } else {

            internetElemento.innerText =
                "SIN INTERNET";

            internetElemento.className =
                "config-value estado-alerta";
        }


        // =============================================
        // BASE DE DATOS
        // =============================================

        document.getElementById(
            "dbEstado"
        ).innerText =
            texto(
                data.database.estado
            );


        document.getElementById(
            "dbMediciones"
        ).innerText =
            texto(
                data.database.mediciones
            );


        document.getElementById(
            "dbEventos"
        ).innerText =
            texto(
                data.database.eventos
            );


        document.getElementById(
            "dbCiclos"
        ).innerText =
            texto(
                data.database.ciclos
            );


        // =============================================
        // AWS
        // =============================================

        document.getElementById(
            "awsPendientes"
        ).innerText =
            texto(
                data.aws.pendientes
            );


        document.getElementById(
            "awsEnviados"
        ).innerText =
            texto(
                data.aws.enviados
            );


        // =============================================
        // PROCESO
        // =============================================

        const proceso =
            document.getElementById(
                "procesoEstado"
            );


        if (
            data.proceso.activo
        ) {

            proceso.innerText =
                `ACTIVO | ID ${data.proceso.id}`;

            proceso.className =
                "config-value estado-activo";

        } else {

            proceso.innerText =
                "INACTIVO";

            proceso.className =
                "config-value estado-inactivo";
        }


        // =============================================
        // ACTUALIZACIÓN
        // =============================================

        document.getElementById(
            "sistemaActualizacion"
        ).innerText =
            formatoFechaSistema(
                data.actualizacion
            );


    } catch (error) {

        console.error(
            "Error cargarSistema:",
            error
        );
    }
}


document.addEventListener(
    "DOMContentLoaded",
    function() {

        cargarSistema();

        setInterval(
            cargarSistema,
            10000
        );
    }
);