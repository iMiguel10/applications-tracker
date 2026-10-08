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

`WEBSITE_DOMAIN` es también el comienzo de los **enlaces de los emails** (recuperar la contraseña): en producción tiene que ser la dirección pública, nunca la de desarrollo.

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

## Enlaces firmados

| Variable | Obligatoria | Qué es |
|---|---|---|
| `APP_SECRET` | Sí | Secreto de al menos 32 caracteres con el que se firman los enlaces de baja de los avisos por email. Genera uno aleatorio, por ejemplo con `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Si falta o es más corto, la API no arranca. Guárdalo como cualquier otra contraseña: quien lo conozca puede dar de baja de los avisos a cualquier usuario. Si lo cambias, los enlaces de baja de los emails ya enviados dejan de funcionar (los usuarios pueden seguir cambiando sus avisos en Preferencias).

## Correo

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_TIMEOUT_SECONDS` y `EMAIL_FROM`. Son opcionales: sin `SMTP_HOST`, la aplicación arranca igual y no envía emails. Ver [Correo](correo.md).

## Límites por cuenta

| Variable | Por defecto | Qué limita |
|---|---|---|
| `LIMIT_APPLICATIONS` | 5000 | Solicitudes por cuenta, archivadas incluidas |
| `LIMIT_COMPANIES` | 2000 | Empresas por cuenta |
| `LIMIT_REMINDERS` | 5000 | Recordatorios por cuenta, en cualquier estado |
| `LIMIT_DOCUMENTS` | 100 | Documentos (CVs y cartas) por cuenta, archivados incluidos |
| `LIMIT_STORAGE_BYTES` | 104857600 (100 MB) | Almacenamiento por cuenta, **en bytes**: la suma de sus documentos, archivados incluidos |
| `DOCUMENT_MAX_BYTES` | 5242880 (5 MB) | Tamaño máximo de cada PDF subido, en bytes. No es por cuenta: vale para todas |

Son opcionales y valen para todas las cuentas. Para dar otro valor a una cuenta concreta, sin tocar las demás:

```bash
docker compose exec api python -m app.scripts.set_user_limit ana@example.com                       # ver su uso y sus límites
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications 10000    # excepción para esa cuenta
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --unlimited  # sin límite
docker compose exec api python -m app.scripts.set_user_limit ana@example.com all --unlimited         # sin límite en todo lo que lo admite
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --reset  # volver al valor global (all --reset, todos)
```

El almacenamiento también va en bytes en el script (`storage_bytes 524288000` son 500 MB) y es el único que **no admite** `--unlimited`: el disco cuesta, y una cuenta sin tope podría llenarlo. `all --unlimited` lo deja como está.

Rebajar un límite por debajo de lo que la cuenta ya tiene no borra nada: solo le impide crear más. Una cuenta sin límite ve en Preferencias cuánto lleva y "sin límite", y nunca recibe avisos.

## Inteligencia artificial

La IA adapta un CV o escribe una carta para una oferta. Hay dos formas de usarla: los **usos gratuitos** de la instalación, con su proveedor y su modelo, y la **clave propia** de cada usuario.

| Variable | Por defecto | Qué es |
|---|---|---|
| `AI_PLATFORM_PROVIDER` | vacía | Proveedor de los usos gratuitos: `groq`, `anthropic`, `openai` u `ollama`. Vacía: no hay uso gratuito |
| `AI_PLATFORM_MODEL` | vacía | Modelo de ese proveedor, por ejemplo `openai/gpt-oss-120b` en Groq |
| `AI_PLATFORM_API_KEY` | vacía | Clave de API de la instalación en ese proveedor. Con Ollama no hace falta |
| `AI_OLLAMA_BASE_URL` | vacía | Dirección de tu Ollama, por ejemplo `http://ollama:11434`. Obligatoria con `AI_PLATFORM_PROVIDER=ollama` |
| `AI_PLATFORM_INPUT_USD_PER_MTOK` | 0 | Precio del modelo por millón de tokens de entrada, en dólares. Solo sirve para estimar el coste de cada uso |
| `AI_PLATFORM_OUTPUT_USD_PER_MTOK` | 0 | Lo mismo para los tokens de salida |
| `AI_REQUEST_TIMEOUT_SECONDS` | 120 | Tiempo máximo de espera de una respuesta del proveedor |
| `AI_KEYS_ENCRYPTION_KEYS` | vacía | Claves maestras con que se cifran las claves de los usuarios, separadas por comas y la nueva primero. Vacía: los usuarios no pueden usar su propia clave |
| `AI_ANTHROPIC_MODELS` | vacía | Modelos que un usuario puede elegir con su clave de Anthropic, separados por comas; el primero es el recomendado. Vacía: Anthropic no se ofrece |
| `AI_OPENAI_MODELS` | vacía | Lo mismo para OpenAI |
| `AI_GROQ_MODELS` | vacía | Lo mismo para Groq |

Si defines `AI_PLATFORM_PROVIDER`, el modelo y la clave son obligatorios: sin ellos, la API no arranca. Para comprobar que funcionan, con una llamada real que cuesta unas decenas de tokens:

```bash
docker compose exec api python -m app.scripts.check_ai_provider
```

La clave se guarda como cualquier otra contraseña: quien la tenga gasta a cargo de tu cuenta en el proveedor. Pon también un tope de gasto en la consola del proveedor.

### Usos gratuitos con tu propio Ollama

Con [Ollama](https://ollama.com) instalado en tu servidor, los usos gratuitos no te cuestan nada por uso. Descarga antes el modelo (`ollama pull gpt-oss:20b`) y configura:

```bash
AI_PLATFORM_PROVIDER=ollama
AI_PLATFORM_MODEL=gpt-oss:20b
AI_OLLAMA_BASE_URL=http://ollama:11434
```

Desde los contenedores, un Ollama instalado en el propio equipo es `http://host.docker.internal:11434`. Un modelo pequeño responde peor y tarda más: comprueba el resultado con `check_ai_provider`.

### Claves propias de los usuarios

Para que cada usuario pueda usar su clave de Anthropic, OpenAI o Groq (sin límite de usos, a su cargo), genera una clave maestra y ponla en `AI_KEYS_ENCRYPTION_KEYS`:

```bash
docker compose exec api python -m app.scripts.rotate_ai_keys --new-key
```

Y elige los modelos de cada proveedor en `AI_ANTHROPIC_MODELS`, `AI_OPENAI_MODELS` y `AI_GROQ_MODELS`. Un proveedor sin modelos no se ofrece. Si retiras de la lista un modelo que alguien usa, su clave se conserva y se le pide que elija otro.

:::danger Guarda la clave maestra con la copia de seguridad
Sin ella, las claves de los usuarios no se pueden descifrar: tendrían que volver a guardarlas. Guárdala aparte de la copia de la base de datos: con las dos, cualquiera podría leer las claves.
:::

Para cambiar la clave maestra sin que nadie pierda la suya: pon la nueva **la primera** en `AI_KEYS_ENCRYPTION_KEYS` sin quitar la antigua, recrea `api` y `worker`, ejecuta `docker compose exec api python -m app.scripts.rotate_ai_keys` y, después, quita la antigua.

## Límite de peticiones

| Variable | Por defecto | Qué es |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Limita los intentos de inicio de sesión, registro y emails, y las peticiones de cada usuario. Solo se desactiva para las pruebas |
| `TRUSTED_PROXIES` | vacía | IPs o redes (CIDR) de tus proxies, separadas por comas, por ejemplo `172.18.0.0/16` |

:::warning Detrás de un proxy, TRUSTED_PROXIES es obligatoria
Si la aplicación está detrás de un proxy (Nginx, un balanceador), todas las peticiones le llegan desde la IP del proxy. Sin `TRUSTED_PROXIES`, todos los usuarios comparten esa IP y el límite de 10 inicios de sesión por minuto se reparte entre todos. Con ella, la aplicación lee la IP real de la cabecera `X-Forwarded-For`, pero solo cuando la pone un proxy de la lista.
:::

Los límites se guardan en Valkey. Si Valkey no responde, la aplicación deja pasar las peticiones sin límite y lo registra en el log, para que nadie se quede sin poder entrar. Mientras dura la caída vuelve a probar cada 30 segundos, y los límites vuelven solos en cuanto Valkey responde.

## Entorno

| Variable | Obligatoria | Qué es |
|---|---|---|
| `ENV` | Sí | `development` o `production`. En `development`, la API registra cada consulta SQL en su log |
