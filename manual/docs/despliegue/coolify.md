---
title: Desplegar con Coolify
sidebar_label: Con Coolify
---

Receta probada con Coolify 4.4 (proxy Traefik) y un dominio con HTTPS de Let's Encrypt. Coolify descarga el repositorio, construye las imágenes en tu servidor, pone el HTTPS y le pasa el tráfico del dominio al servicio `web`. Los nombres de los menús de Coolify pueden cambiar entre versiones.

## Antes de empezar

- Cumples los [requisitos](requisitos.md): Coolify funcionando, un dominio que apunta al servidor y los puertos 80 y 443 abiertos.
- Tienes preparadas las [variables](variables.md) obligatorias, con sus secretos ya generados.

## 1. Crear el recurso

1. En tu proyecto de Coolify, **+ New** y elige el repositorio de Git (el tuyo, si has hecho un fork, o el público del proyecto).
2. Como tipo de construcción (*Build Pack*), **Docker Compose**.
3. Rama `main`, *Base Directory* `/` y *Docker Compose Location* `/compose.prod.yml`.

Coolify lee el fichero y lista sus servicios: `web`, `api`, `worker`, `db`, `supertokens-db`, `supertokens`, `valkey` y `backup`.

## 2. Asignar el dominio

El dominio va **solo** en el servicio `web`, con `https://`:

```text
https://tracker.example.com
```

Los demás servicios no llevan dominio. Si se lo pones a otro, el proxy publicaría por internet servicios internos.

## 3. Variables

En *Environment Variables* del recurso, Coolify muestra las que el compose menciona. Rellena al menos las obligatorias (ver [Variables](variables.md)):

| Variable | Valor |
|---|---|
| `APP_URL` | El mismo dominio, `https://tracker.example.com`, sin barra final |
| `POSTGRES_PASSWORD`, `SUPERTOKENS_DB_PASSWORD`, `SUPERTOKENS_API_KEY`, `APP_SECRET` | Cuatro valores distintos, generados con `openssl rand -hex 32` |

**Guarda estos cuatro secretos en un gestor de contraseñas ahora**: las copias de seguridad no los incluyen y los necesitarás para [restaurar](copias-de-seguridad.md).

Si quieres que los usuarios puedan usar su propia clave de IA, genera y añade también `AI_KEYS_ENCRYPTION_KEYS` (ver [Variables](variables.md)). El correo y la IA de la plataforma puedes dejarlos para después.

## 4. Primer despliegue

Pulsa **Deploy**. La primera vez construye las imágenes en el servidor y tarda unos minutos (unos 7 en las pruebas). Si falta una variable obligatoria, el despliegue falla enseguida con su nombre en el log: añádela y vuelve a desplegar.

**Qué debe verse:** los ocho servicios en marcha (*Running*) y, pasado un minuto, sin avisos de *unhealthy*. Coolify pide el certificado la primera vez que el dominio recibe tráfico.

## 5. Comprobar

```bash
curl https://tracker.example.com/api/v1/health
```

Debe responder `{"status":"ok","database":"ok","environment":"production"}`. En el navegador, `https://tracker.example.com` muestra el inicio de sesión (con el candado del certificado) y `https://tracker.example.com/manual/` este manual.

Si `health` falla en el primer minuto, la API aún está aplicando las migraciones: espera y repite.

## 6. Crear la primera cuenta

El registro viene cerrado. Crea tu cuenta con [el script de cuentas](cuentas.md); es el último paso para poder entrar.

## Comandos de mantenimiento

Algunos pasos (crear cuentas, la copia a mano, restaurar) se ejecutan dentro de un contenedor. Hay dos formas:

- **La terminal de Coolify:** en el recurso, abre la terminal del servicio (`api`, `backup`…).
- **Por SSH, con Docker**, si la terminal del panel no funciona. Los contenedores se llaman `<servicio>-<uuid>-<fecha>`; búscalos con:

    ```bash
    docker ps --format '{{.Names}}' | grep api
    docker exec -it <contenedor-api> python -m app.scripts.create_user ana@example.com
    ```

El nombre del contenedor **cambia con cada despliegue**: vuelve a buscarlo.

## Siguientes pasos

- [Correo](correo.md) y [IA de la plataforma](ia-de-la-plataforma.md), cuando los quieras.
- [Despliegue continuo](despliegue-continuo.md): que cada versión nueva se despliegue sola tras pasar la CI.
- [Copias de seguridad](copias-de-seguridad.md): comprueba que la primera sale bien.
