---
title: Variables de entorno
sidebar_label: Variables de entorno
---

Toda la configuración va en un fichero `.env` en la raíz del proyecto. El repositorio trae una plantilla, `.env.example`, con los valores de desarrollo:

```bash
cp .env.example .env
```

:::danger Antes de exponer la instalación
Cambia **todas** las contraseñas y la clave de SuperTokens por valores largos y aleatorios, y no subas nunca el `.env` a un repositorio. Por ejemplo, para generar un valor:

```bash
openssl rand -hex 32
```
:::

Una variable nueva del `.env` no se aplica con un simple reinicio: el contenedor lee el fichero al **crearse**. Tras cambiarlo:

```bash
docker compose up -d --force-recreate
```

## Base de datos de la aplicación

| Variable | Obligatoria | Qué es |
|---|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Sí | Base de datos, usuario y contraseña que crea el contenedor `db` la primera vez que arranca |
| `DATABASE_URL` | Sí | Cómo se conecta la API: `postgresql+asyncpg://USUARIO:CONTRASEÑA@db:5432/BASE`, con los mismos valores de arriba |

## Autenticación (SuperTokens)

| Variable | Obligatoria | Qué es |
|---|---|---|
| `SUPERTOKENS_DB_NAME`, `SUPERTOKENS_DB_USER`, `SUPERTOKENS_DB_PASSWORD` | Sí | Base de datos propia de SuperTokens |
| `SUPERTOKENS_CONNECTION_URI` | Sí | Dirección interna del servicio: `http://supertokens:3567` |
| `SUPERTOKENS_API_KEY` | Sí | Clave compartida entre la API y SuperTokens, de **al menos 20 caracteres** |
| `API_DOMAIN` | Sí | URL pública de la API, por ejemplo `https://api.tudominio.com` |
| `WEBSITE_DOMAIN` | Sí | URL pública de la aplicación web, por ejemplo `https://tudominio.com` |

`API_DOMAIN` y `WEBSITE_DOMAIN` deciden a qué sitio pertenecen las cookies de sesión. Tienen que coincidir **exactamente** con las direcciones que escribe el usuario en el navegador: `localhost` y `127.0.0.1` son sitios distintos para el navegador, y si no coinciden el inicio de sesión parece no funcionar, sin ningún error.

## Aplicación web

| Variable | Obligatoria | Qué es |
|---|---|---|
| `CORS_ORIGINS` | Sí | Orígenes que pueden llamar a la API desde un navegador, separados por comas. Normalmente, el mismo valor que `WEBSITE_DOMAIN` |
| `VITE_API_URL` | Sí | URL de la API que usa la aplicación web. Normalmente, el mismo valor que `API_DOMAIN` |

## Cola de tareas y ficheros

| Variable | Obligatoria | Qué es |
|---|---|---|
| `VALKEY_URL` | Sí | Dirección de Valkey: `redis://valkey:6379/0` |
| `FILES_ROOT` | Sí | Carpeta de los ficheros dentro de los contenedores: `/data/files` (el volumen `files_data`) |

Si falta alguna de estas dos, la API no arranca.

## Correo

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_TIMEOUT_SECONDS` y `EMAIL_FROM`. Son opcionales: sin `SMTP_HOST`, la aplicación arranca igual y no envía emails. Ver [Correo](correo.md).

## Entorno

| Variable | Obligatoria | Qué es |
|---|---|---|
| `ENV` | Sí | `development` o `production`. En `development`, la API registra cada consulta SQL en su log |
