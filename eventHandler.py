import util
import yaml
def pyp_Conect():
    """
    Lee la configuración desde el archivo pyp_Conect.yml y construye
    el payload de conexión inicial con hora, grupo, valores y unidades.
    """
    config = util.cargar_configuracion(
        '/home/pi/.scr/.scr/RPI-MDFR/device/pyp_Conect.yml',
        'pyp_connect'
    )
    # Datos base
    id_device = config.get('id_device')
    g = config.get('g', id_device)

    valores = []
    unidades = []

    # Recorre los registros del YAML
    for reg in config.get('registers', []):
        valores.append(str(reg.get('v', '')))
        unidades.append(str(reg.get('u', '')))

    params = {
        "t": util.get__time_utc(),
        "g": g,
        "v": valores,
        "u": unidades
    }

    return {"d": [params]} 
