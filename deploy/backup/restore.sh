#!/bin/sh
# Restaura una copia de /backups (F7): las dos BD y los ficheros, sustituyendo lo que
# haya. Procedimiento completo en el manual (Despliegue › Copias de seguridad):
#
#   1. Parar api, worker y supertokens: nada debe escribir mientras se restaura.
#   2. docker compose -f compose.prod.yml run --rm backup restore <copia> --yes
#   3. Arrancar de nuevo el stack: api aplica las migraciones que falten.
#
# <copia> es el nombre de su carpeta (2026-10-19_030000). Una copia traída de fuera
# (el NAS, el S3) se deja antes en la carpeta de copias del servidor.
set -eu

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') | restore | $*"; }
die() { log "ERROR: $*"; exit 1; }

name="${1:-}"
confirm="${2:-}"
[ -n "$name" ] || die "uso: restore <copia> --yes   (copias: $(ls -1 /backups | tr '\n' ' '))"
dir="/backups/$name"
[ -d "$dir" ] || die "no existe la copia $name en /backups"
[ "$confirm" = "--yes" ] || die "esto SUSTITUYE las BD y los ficheros actuales por la copia $name; repite con --yes"

log "comprobando la integridad de la copia $name"
(cd "$dir" && sha256sum -c SHA256SUMS) || die "la copia está dañada: no se toca nada"

# Nadie más conectado: con api, worker o el core en marcha, sus escrituras se
# mezclarían con la copia.
others() {
    PGPASSWORD="$2" psql -h "$1" -U "$3" -d "$4" -tAc \
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()"
}
[ "$(others "$APP_DB_HOST" "$APP_DB_PASSWORD" "$APP_DB_USER" "$APP_DB_NAME")" = "0" ] \
    || die "hay conexiones a la BD de la aplicación: para api y worker antes de restaurar"
[ "$(others "$AUTH_DB_HOST" "$AUTH_DB_PASSWORD" "$AUTH_DB_USER" "$AUTH_DB_NAME")" = "0" ] \
    || die "hay conexiones a la BD de SuperTokens: para supertokens antes de restaurar"

# Se vacía el esquema entero en lugar de `pg_restore --clean`: con --clean, las tablas
# que la copia no conoce (una migración posterior) seguirían ahí, y alembic, al
# arrancar, intentaría crearlas de nuevo.
#
# Vaciar y restaurar van en UNA transacción: si la restauración fallara a mitad, la
# BD se queda como estaba en lugar de vacía. Por eso el volcado se pasa antes a SQL
# en un fichero (pg_restore -f) y no por una tubería: si pg_restore fallara a mitad
# de la tubería, psql recibiría el SQL cortado y lo confirmaría igual.
restore_db() {
    host=$1 password=$2 user=$3 db=$4 dump=$5
    log "restaurando $db"
    sql=$(mktemp)
    {
        echo "DROP SCHEMA public CASCADE;"
        echo "CREATE SCHEMA public;"
    } > "$sql"
    pg_restore --no-owner --file=- "$dir/$dump" >> "$sql" \
        || { rm -f "$sql"; die "no se pudo leer $dump: no se ha tocado $db"; }
    PGPASSWORD="$password" psql -h "$host" -U "$user" -d "$db" -q -X \
        -v ON_ERROR_STOP=1 --single-transaction -f "$sql" > /dev/null \
        || { rm -f "$sql"; die "la restauración de $db falló y se deshizo: $db sigue como estaba"; }
    rm -f "$sql"
}
restore_db "$APP_DB_HOST" "$APP_DB_PASSWORD" "$APP_DB_USER" "$APP_DB_NAME" app.dump
restore_db "$AUTH_DB_HOST" "$AUTH_DB_PASSWORD" "$AUTH_DB_USER" "$AUTH_DB_NAME" supertokens.dump

log "restaurando los ficheros"
find /data/files -mindepth 1 -delete
tar -xzf "$dir/files.tar.gz" -C /data/files
# Del usuario de la API (uid 1000, backend/Dockerfile), que es quien escribe ahí.
chown -R 1000:1000 /data/files

log "copia $name restaurada: arranca de nuevo el stack"
