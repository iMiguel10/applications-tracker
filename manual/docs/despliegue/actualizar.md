---
title: Actualizar a una versión nueva
sidebar_label: Actualizar
---

Actualizar es **volver a desplegar** la versión nueva del repositorio. No hay que ejecutar nada a mano.

- **Con Coolify:** **Deploy**, o automáticamente con el [despliegue continuo](despliegue-continuo.md).
- **Sin Coolify:** `git pull` y `docker compose -f compose.prod.yml up -d --build`.

## Qué pasa

- **Las migraciones son automáticas.** Al arrancar, `api` aplica las migraciones pendientes de la base de datos antes de aceptar peticiones. El `worker` espera a que `api` esté sano, así que nunca corre con un esquema antiguo.
- **Los datos se conservan.** Las bases de datos, Valkey y los ficheros viven en volúmenes que un despliegue no toca.
- **Puede haber unos segundos sin servicio** mientras `api` se recrea y migra: si la web te da un error 502, la API aún no está lista; espera y recarga.
- **Si cambias `APP_URL`** (otro dominio), la imagen `web` se reconstruye, porque el frontend lleva la dirección dentro. Cambiar de dominio también invalida las sesiones abiertas, porque las cookies son del dominio anterior.
- **Si cambias una variable**, el servicio afectado se recrea al desplegar. Un reinicio no la aplica.

## Antes de actualizar

**Haz una copia.** Una migración no se deshace sola. Si el servicio `backup` ya hizo la de esta noche, vale; si no, haz otra ahora (ver [Copias de seguridad](copias-de-seguridad.md)) y comprueba que terminó.

## Si algo sale mal

Si la versión nueva no arranca, `api` queda *unhealthy* y el despliegue falla; el log dice por qué (normalmente, una variable obligatoria nueva sin poner). Añádela y vuelve a desplegar. Si una migración dejó los datos mal, [restaura](copias-de-seguridad.md) la copia de antes.
