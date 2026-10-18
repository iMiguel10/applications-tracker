#!/bin/sh
# Healthcheck del servicio `backup`: enfermo si la última copia falló, o si la última
# correcta tiene más de BACKUP_MAX_AGE_HOURS. Se cuenta desde la última copia o desde
# que arrancó el contenedor, lo más reciente: recién desplegado, aunque la última copia
# sea antigua, tiene ese margen para hacer la siguiente.
set -eu

max_age=$(( ${BACKUP_MAX_AGE_HOURS:-26} * 3600 ))
now=$(date +%s)
started=$(stat -c %Y /proc/1)

last_success=$(cat /backups/.last_success 2>/dev/null || echo 0)
last_failure=$(cat /backups/.last_failure 2>/dev/null || echo 0)

if [ "$last_failure" -gt "$last_success" ]; then
    echo "la última copia falló (ver los logs del contenedor)"
    exit 1
fi

reference=$last_success
[ "$started" -gt "$reference" ] && reference=$started
if [ $((now - reference)) -gt "$max_age" ]; then
    echo "ninguna copia correcta en las últimas ${BACKUP_MAX_AGE_HOURS:-26} horas"
    exit 1
fi
