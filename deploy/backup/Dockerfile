# Servicio `backup` de producción (F7): copia cada noche las dos BD y los ficheros a
# una carpeta del servidor y, si se configura, también fuera con rclone. La imagen de
# Postgres trae pg_dump y pg_restore de la misma versión que las BD (17).
FROM postgres:17-alpine

# tzdata: la hora de BACKUP_SCHEDULE es la de TZ. rclone: el envío opcional fuera
# del servidor (BACKUP_RCLONE_REMOTE).
RUN apk add --no-cache rclone tzdata

COPY --chmod=755 deploy/backup/backup.sh /usr/local/bin/backup
COPY --chmod=755 deploy/backup/restore.sh /usr/local/bin/restore
COPY --chmod=755 deploy/backup/healthcheck.sh /usr/local/bin/backup-healthcheck
COPY --chmod=755 deploy/backup/entrypoint.sh /usr/local/bin/backup-entrypoint

# Se sobrescribe el entrypoint de Postgres: este contenedor no arranca ninguna BD.
ENTRYPOINT ["backup-entrypoint"]
# Sin argumentos, programa la copia con cron. `backup` o `restore <copia>`, a mano.
CMD ["cron"]

# Unhealthy si la última copia correcta tiene más de BACKUP_MAX_AGE_HOURS: el fallo
# de una copia nocturna se ve en el panel en lugar de descubrirse al necesitarla.
HEALTHCHECK --interval=10m --timeout=10s --start-period=1m --retries=1 \
    CMD backup-healthcheck
