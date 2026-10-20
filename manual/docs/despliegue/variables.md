---
title: Variables de entorno
sidebar_label: Variables de entorno
---

La configuración de producción son pocas variables. En **Coolify** van en *Environment Variables* del recurso; **sin Coolify**, en un fichero `.env` junto a `compose.prod.yml`. El repositorio trae la plantilla, `.env.prod.example`, con cada variable explicada:

```bash
cp .env.prod.example .env
```

Cambiar una variable exige **volver a desplegar** (en Coolify, **Deploy**; sin él, `docker compose -f compose.prod.yml up -d --build`). Un reinicio no basta: el contenedor lee sus variables al crearse. `APP_URL` además reconstruye la imagen `web`, que la lleva dentro.

:::danger Los secretos
Genera cada contraseña y clave **distinta**, larga y aleatoria, por ejemplo con `openssl rand -hex 32`. No las subas a un repositorio y guárdalas en un gestor de contraseñas: las [copias de seguridad](copias-de-seguridad.md) no las incluyen.
:::

Si falta una variable obligatoria, el despliegue falla antes de arrancar nada y el mensaje dice cuál.

## Obligatorias

| Variable | Qué es |
|---|---|
| `APP_URL` | Dirección pública de la aplicación, con `https://` y **sin barra final**: `https://tracker.example.com`. Es la web, la API y el comienzo de los enlaces de los emails. Tiene que coincidir **exactamente** con lo que escribe el usuario en el navegador, porque de ella dependen las cookies de sesión |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos de la aplicación |
| `SUPERTOKENS_DB_PASSWORD` | Contraseña de la base de datos de SuperTokens |
| `SUPERTOKENS_API_KEY` | Clave compartida entre la API y SuperTokens, de al menos 20 caracteres |
| `APP_SECRET` | Secreto de al menos 32 caracteres con el que se firman los enlaces de baja de los avisos. Si lo cambias, los enlaces de baja de los emails ya enviados dejan de funcionar (los usuarios pueden seguir cambiando sus avisos en Preferencias) |

Cambiar `POSTGRES_PASSWORD` o `SUPERTOKENS_DB_PASSWORD` **después del primer arranque** no cambia la contraseña dentro de la base de datos, que se fijó al crearla: la aplicación dejaría de conectarse. Elígelas bien desde el principio.

## Registro

| Variable | Por defecto | Qué es |
|---|---|---|
| `SIGNUP_ENABLED` | `false` | Con `false`, nadie puede crearse una cuenta: el inicio de sesión no lo ofrece y la página de registro explica que está cerrado. Las cuentas las creas tú ([Cuentas](cuentas.md)). Con `true`, cualquiera puede registrarse |
| `DEMO_PASSWORD` | vacía | Contraseña de la [cuenta de demostración](cuentas.md#cuenta-de-demostración). Solo la lee el script `reset_demo`; sin ella, el script no hace nada |

## Textos legales

Si das cuentas a otras personas, pon al menos el nombre y el contacto: la aplicación publica entonces su aviso legal, su política de privacidad, sus términos y su política de cookies, y pide aceptarlos. Sin ellos, la instalación se trata como de uso personal. Ver [Tus obligaciones como responsable](obligaciones.md#informar-a-tus-usuarios).

| Variable | Por defecto | Qué es |
|---|---|---|
| `LEGAL_OPERATOR_NAME` | vacía | Tu nombre o el de tu entidad: el responsable de los datos |
| `LEGAL_CONTACT_EMAIL` | vacía | El email al que se escribe para dudas y para ejercer los derechos |
| `LEGAL_ADDRESS` | vacía | Dirección postal, si quieres publicarla |
| `LEGAL_TAX_ID` | vacía | Tu NIF, si quieres publicarlo |
| `LEGAL_SUPERVISORY_AUTHORITY` | vacía (la AEPD) | La autoridad de control ante la que reclamar, si no es la española. Se escribe tal cual en la política: `la CNIL (www.cnil.fr)` |

## Claves de IA propias de los usuarios

| Variable | Por defecto | Qué es |
|---|---|---|
| `AI_KEYS_ENCRYPTION_KEYS` | vacía | Claves maestras con que se cifran las claves de API que guardan los usuarios, separadas por comas y la nueva primero. Vacía: los usuarios no pueden usar su propia clave |
| `AI_ANTHROPIC_MODELS` | los de `compose.prod.yml` | Modelos que un usuario puede elegir con su clave de Anthropic, separados por comas; el primero es el recomendado. Vacía: Anthropic no se ofrece |
| `AI_OPENAI_MODELS` | los de `compose.prod.yml` | Lo mismo para OpenAI |
| `AI_GROQ_MODELS` | los de `compose.prod.yml` | Lo mismo para Groq |

Para generar una clave maestra, desde la terminal del servicio `api` (o con `docker exec -it <contenedor-api> …`):

```bash
python -m app.scripts.rotate_ai_keys --new-key
```

Imprime una clave nueva; cópiala en `AI_KEYS_ENCRYPTION_KEYS`. Si retiras de la lista un modelo que alguien usa, su clave se conserva y se le pide que elija otro.

:::danger Guarda la clave maestra aparte
Sin ella, las claves que guardaron los usuarios no se pueden descifrar y tendrían que volver a introducirlas. Guárdala **fuera** de las copias de seguridad de la base de datos: con las dos, cualquiera podría leer las claves.
:::

Para cambiarla sin que nadie pierda la suya: pon la nueva **la primera** en `AI_KEYS_ENCRYPTION_KEYS` sin quitar la antigua, vuelve a desplegar, ejecuta `python -m app.scripts.rotate_ai_keys` en el servicio `api` y, después, quita la antigua y despliega otra vez.

## Correo

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` y `SMTP_TIMEOUT_SECONDS` (segundos de espera de cada envío, 30 por defecto). Opcionales: sin `SMTP_HOST`, la aplicación arranca igual y no envía emails. Ver [Correo](correo.md).

## IA de la plataforma

`AI_PLATFORM_PROVIDER`, `AI_PLATFORM_MODEL`, `AI_PLATFORM_API_KEY`, `AI_PLATFORM_INPUT_USD_PER_MTOK`, `AI_PLATFORM_OUTPUT_USD_PER_MTOK`, `AI_OLLAMA_BASE_URL`, `AI_OLLAMA_CONTEXT_TOKENS`, `AI_REQUEST_TIMEOUT_SECONDS`, `LIMIT_AI_CV_PROPOSALS` y `LIMIT_AI_COVER_LETTER_PROPOSALS`. Opcionales: sin `AI_PLATFORM_PROVIDER` no hay usos gratuitos. Cada una, en [IA de la plataforma](ia-de-la-plataforma.md).

## Límites por cuenta

| Variable | Por defecto | Qué limita |
|---|---|---|
| `LIMIT_APPLICATIONS` | 5000 | Solicitudes por cuenta, archivadas incluidas |
| `LIMIT_COMPANIES` | 2000 | Empresas por cuenta |
| `LIMIT_REMINDERS` | 5000 | Recordatorios por cuenta, en cualquier estado |
| `LIMIT_DOCUMENTS` | 100 | Documentos (CVs y cartas) por cuenta, archivados incluidos |
| `LIMIT_STORAGE_BYTES` | 104857600 (100 MB) | Almacenamiento por cuenta, **en bytes**: la suma de sus documentos, archivados incluidos |
| `DOCUMENT_MAX_BYTES` | 5242880 (5 MB) | Tamaño máximo de cada PDF subido, en bytes. No es por cuenta: vale para todas. El servidor web admite cuerpos de hasta 25 MB, así que no pongas más |

Son opcionales y valen para todas las cuentas. Para dar otro valor a una cuenta concreta, sin tocar las demás, ejecuta en el servicio `api` (por la terminal de Coolify o con `docker exec -it <contenedor-api>`; sin Coolify, `docker compose -f compose.prod.yml exec api`):

```bash
python -m app.scripts.set_user_limit ana@example.com                          # ver su uso y sus límites
python -m app.scripts.set_user_limit ana@example.com applications 10000       # excepción para esa cuenta
python -m app.scripts.set_user_limit ana@example.com applications --unlimited # sin límite
python -m app.scripts.set_user_limit ana@example.com all --unlimited          # sin límite en todo lo que lo admite
python -m app.scripts.set_user_limit ana@example.com applications --reset     # volver al valor global (all --reset, todos)
```

El almacenamiento también va en bytes en el script (`storage_bytes 524288000` son 500 MB) y es el único que **no admite** `--unlimited`: el disco cuesta, y una cuenta sin tope podría llenarlo. `all --unlimited` lo deja como está.

Rebajar un límite por debajo de lo que la cuenta ya tiene no borra nada: solo le impide crear más. Una cuenta sin límite ve en Preferencias cuánto lleva y "sin límite", y nunca recibe avisos.

## Base de datos

| Variable | Por defecto | Qué es |
|---|---|---|
| `POSTGRES_DB` | `applications_tracker` | Nombre de la base de datos de la aplicación |
| `POSTGRES_USER` | `applications_tracker` | Su usuario |

Como las contraseñas, solo se fijan al crear la base de datos: no los cambies en una instalación que ya tiene datos.

## Copias de seguridad

`BACKUP_HOST_DIR`, `TZ`, `BACKUP_SCHEDULE`, `BACKUP_KEEP_DAILY`, `BACKUP_KEEP_WEEKLY`, `BACKUP_MAX_AGE_HOURS` y `BACKUP_RCLONE_REMOTE`. Todas opcionales, explicadas en [Copias de seguridad](copias-de-seguridad.md).

## Límite de peticiones y proxies

El límite de peticiones (10 inicios de sesión por minuto por IP, 600 peticiones por minuto por usuario…) está activo y **no se configura**: el servidor web aplica la primera capa por IP y la API, la segunda por IP, email y usuario. Tampoco hay que tocar `TRUSTED_PROXIES`: `compose.prod.yml` la fija a las redes privadas, porque a la API solo llegan contenedores. Por eso no debes publicar el puerto de la API (ver [Sin Coolify](sin-coolify.md)).

Los límites se guardan en Valkey. Si Valkey no responde, la aplicación deja pasar las peticiones sin límite y lo registra en el log, para que nadie se quede sin poder entrar. Mientras dura la caída vuelve a probar cada 30 segundos, y los límites vuelven solos en cuanto Valkey responde.
