#!/bin/sh
# Una copia completa (F7): las dos BD y los ficheros, en /backups/<fecha>_<hora>/.
#
# Orden: BD de la aplicación, BD de SuperTokens y, por último, los ficheros.
# - Los ficheros, después de la BD: el fichero se escribe antes que su fila
#   (invariante 15), así que todo documento de la copia tiene su fichero; como
#   mucho sobra alguno, que el barrido de huérfanos limpia tras restaurar.
# - SuperTokens, después de la aplicación: una cuenta creada entre los dos volcados
#   solo carece de su fila en `users`, que la API crea en su siguiente inicio de
#   sesión (get_or_create). Al revés quedarían filas de `users` sin cuenta.
#
# La copia se escribe en una carpeta `.partial` y se renombra al terminar: una copia
# a medias (un corte, un disco lleno) nunca parece completa.
set -eu

BACKUPS=/backups
FILES=/data/files

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') | backup | $*"; }

fail() {
    log "ERROR: $*"
    date +%s > "$BACKUPS/.last_failure"
    exit 1
}

# Las BACKUP_KEEP_DAILY más recientes y, además, la última de cada una de las
# BACKUP_KEEP_WEEKLY semanas ISO anteriores sin copia diaria (una semana que ya
# tiene diarias no gasta un hueco semanal). Solo carpetas de copias completas.
prune() {
    keep_daily="${BACKUP_KEEP_DAILY:-7}"
    keep_weekly="${BACKUP_KEEP_WEEKLY:-4}"
    i=0
    seen=""
    weekly=0
    for dir in $(ls -1d "$BACKUPS"/????-??-??_?????? 2>/dev/null | sort -r); do
        i=$((i + 1))
        day=$(basename "$dir" | cut -c1-10)
        week=$(date -d "$day 00:00" +%G-%V)
        if [ "$i" -le "$keep_daily" ]; then
            seen="$seen $week"
            continue
        fi
        case " $seen " in
            *" $week "*) ;;
            *)
                if [ "$weekly" -lt "$keep_weekly" ]; then
                    seen="$seen $week"
                    weekly=$((weekly + 1))
                    continue
                fi
                ;;
        esac
        log "borrando la copia antigua $(basename "$dir")"
        rm -rf "$dir"
    done
}

mkdir -p "$BACKUPS"
# Restos de una copia que no terminó (el contenedor se paró a mitad).
rm -rf "$BACKUPS"/*.partial

# Con segundos: dos copias seguidas (una manual tras la programada) no comparten nombre.
name=$(date +%Y-%m-%d_%H%M%S)
[ -e "$BACKUPS/$name" ] && fail "ya existe una copia llamada $name"
partial="$BACKUPS/$name.partial"
mkdir -p "$partial"
log "empieza la copia $name"

PGPASSWORD="$APP_DB_PASSWORD" pg_dump -h "$APP_DB_HOST" -U "$APP_DB_USER" \
    -d "$APP_DB_NAME" --format=custom --file="$partial/app.dump" \
    || { rm -rf "$partial"; fail "pg_dump de la BD de la aplicación"; }

PGPASSWORD="$AUTH_DB_PASSWORD" pg_dump -h "$AUTH_DB_HOST" -U "$AUTH_DB_USER" \
    -d "$AUTH_DB_NAME" --format=custom --file="$partial/supertokens.dump" \
    || { rm -rf "$partial"; fail "pg_dump de la BD de SuperTokens"; }

tar -czf "$partial/files.tar.gz" -C "$FILES" . \
    || { rm -rf "$partial"; fail "tar de los ficheros"; }

# Para comprobar al restaurar que nada se corrompió por el camino (el NAS, el S3).
(cd "$partial" && sha256sum app.dump supertokens.dump files.tar.gz > SHA256SUMS)

mv "$partial" "$BACKUPS/$name"
log "copia local lista: $name ($(du -sh "$BACKUPS/$name" | cut -f1))"

prune

# Fuera del servidor, opcional. Una cadena de conexión de rclone con el destino, por
# ejemplo ":s3,provider=Cloudflare,access_key_id=…,secret_access_key=…,endpoint=…:bucket/carpeta".
# `copy`, nunca `sync`: si alguien borra las copias del servidor, las de fuera siguen
# ahí. Su retención la ponen las reglas del propio almacenamiento.
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
    log "enviando la copia fuera del servidor"
    rclone copy --quiet "$BACKUPS/$name" "$BACKUP_RCLONE_REMOTE/$name" \
        || fail "rclone no pudo enviar la copia $name (la local sí está)"
    log "copia enviada fuera del servidor"
fi

date +%s > "$BACKUPS/.last_success"
log "copia $name terminada"
