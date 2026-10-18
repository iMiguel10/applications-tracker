#!/bin/sh
# Arranque del servicio `backup`: `cron` (por defecto) programa la copia; cualquier
# otro comando (`backup`, `restore …`) se ejecuta tal cual.
set -eu

if [ "${1:-cron}" != "cron" ]; then
    exec "$@"
fi

schedule="${BACKUP_SCHEDULE:-0 3 * * *}"
echo "Copias programadas: '$schedule' (TZ=${TZ:-UTC}) en /backups"

# crond de busybox no pasa el entorno del contenedor a sus tareas: se guarda aquí
# (solo legible por root) y la tarea lo carga antes de copiar.
export -p > /run/backup.env
chmod 600 /run/backup.env
mkdir -p /etc/crontabs
echo "$schedule . /run/backup.env && backup > /proc/1/fd/1 2> /proc/1/fd/2" > /etc/crontabs/root

# En primer plano: los registros de cada copia salen en los logs del contenedor.
exec crond -f -l 8
