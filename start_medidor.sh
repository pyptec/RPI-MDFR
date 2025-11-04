#!/bin/bash
# Activar entorno virtual
source /home/pi/.scr/bin/activate

# Esperar 5 segundos antes de ejecutar el script en Python
sleep 5

# Ejecutar el script en Python
python /home/pi/.scr/.scr/RPI-MDFR/rpi-mdfr.py
