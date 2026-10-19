#!/bin/sh
# Despliegue continuo (F7, 0023): lo llama el job `deploy` de la CI cuando un push a
# main pasa todo lo demás. Pide el despliegue a la API de Coolify, espera a que
# termine y comprueba la aplicación ya desplegada.
#
# Variables: COOLIFY_URL, COOLIFY_TOKEN (permiso de despliegue), COOLIFY_APP_UUID,
# PRODUCTION_URL y EXPECTED_SHA (el commit que ha pasado la CI).
#
# Coolify despliega siempre lo último de la rama, no un commit concreto: si main ya
# ha avanzado, desplegar aquí subiría un commit que esta CI no ha probado. Ese caso
# se salta sin fallar; lo despliega la CI del commit nuevo cuando pase.
set -eu

: "${COOLIFY_URL:?}" "${COOLIFY_TOKEN:?}" "${COOLIFY_APP_UUID:?}"
: "${PRODUCTION_URL:?}" "${EXPECTED_SHA:?}"
# Sin barra final: con ella, las llamadas saldrían como //api/v1.
COOLIFY_URL=${COOLIFY_URL%/}
PRODUCTION_URL=${PRODUCTION_URL%/}

# api <método> <ruta>. Lanzar un despliegue es POST desde Coolify 4.4 (antes, GET:
# con GET responde 405).
api() {
    curl -fsS --max-time 30 -X "$1" -H "Authorization: Bearer $COOLIFY_TOKEN" \
        -H "Accept: application/json" "$COOLIFY_URL/api/v1/$2"
}

head_sha=$(git ls-remote origin refs/heads/main | cut -f1)
if [ "$head_sha" != "$EXPECTED_SHA" ]; then
    echo "main ya está en $head_sha, no en $EXPECTED_SHA: lo desplegará la CI de ese commit."
    exit 0
fi

deployment=$(api POST "deploy?uuid=$COOLIFY_APP_UUID&force=false" \
    | jq -r '.deployments[0].deployment_uuid // empty')
[ -n "$deployment" ] || { echo "Coolify no devolvió ningún despliegue" >&2; exit 1; }
echo "Despliegue $deployment en cola"

# Construye en el servidor: unos 6 minutos. Se espera hasta 30.
status=""
i=0
while [ "$i" -lt 180 ]; do
    i=$((i + 1))
    sleep 10
    info=$(api GET "deployments/$deployment") || continue
    status=$(echo "$info" | jq -r '.status')
    case "$status" in
        finished) break ;;
        failed|cancelled*)
            echo "El despliegue terminó en '$status'; el log, en el panel de Coolify" >&2
            exit 1 ;;
    esac
done
[ "$status" = "finished" ] || { echo "El despliegue no terminó en 30 minutos" >&2; exit 1; }

deployed=$(echo "$info" | jq -r '.commit // empty')
if [ -n "$deployed" ] && [ "$deployed" != "$EXPECTED_SHA" ]; then
    echo "Coolify desplegó $deployed y no $EXPECTED_SHA (main avanzó a la vez)" >&2
    exit 1
fi
echo "Desplegado $EXPECTED_SHA"

# La API recién arrancada puede tardar unos segundos (migraciones).
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if curl -fsS --max-time 10 "$PRODUCTION_URL/api/v1/health" | grep -q '"status":"ok"'; then
        echo "$PRODUCTION_URL responde"
        exit 0
    fi
    sleep 10
done
echo "$PRODUCTION_URL/api/v1/health no responde tras el despliegue" >&2
exit 1
