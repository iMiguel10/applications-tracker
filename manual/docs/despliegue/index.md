---
title: Desplegar Applications Tracker
sidebar_label: Visión general
---

Applications Tracker se despliega con **Docker Compose**: todos sus servicios son contenedores y la configuración va en variables de entorno. El repositorio trae el fichero de producción, `compose.prod.yml`, y hay dos formas probadas de usarlo:

- [**Con Coolify**](coolify.md): lo construye en tu servidor, pone el HTTPS y puede desplegar cada versión nueva desde la CI. Es la receta de referencia.
- [**Sin Coolify**](sin-coolify.md): `docker compose` y cualquier proxy con HTTPS delante.

## Qué se despliega

Un solo dominio sirve la aplicación web, el manual y la API. El servicio `web` (un Nginx) es lo único que recibe tráfico: el proxy de HTTPS le pasa todo el dominio y él reparte.

| Servicio | Qué hace | ¿Guarda datos? |
|---|---|---|
| `web` | Sirve la aplicación web y este manual (en `/manual/`), y reparte `/api/` y `/auth/` a la API. Limita las peticiones por IP y pone las cabeceras de seguridad | No |
| `api` | La API (FastAPI). Al arrancar, **aplica sola las migraciones** de la base de datos | No |
| `worker` | Ejecuta en segundo plano las tareas lentas: enviar emails, generar PDFs, llamar a la IA y programar los avisos. Debe estar en marcha | No |
| `db` | PostgreSQL con los datos de la aplicación | **Sí** |
| `supertokens` | Servicio de autenticación (cuentas y sesiones) | No |
| `supertokens-db` | PostgreSQL propio de SuperTokens: cuentas y contraseñas | **Sí** |
| `valkey` | Cola de tareas pendientes y contadores del límite de peticiones | Solo tareas en espera, no datos |
| `backup` | Copia cada noche las dos bases de datos y los ficheros. Ver [Copias de seguridad](copias-de-seguridad.md) | Las copias (en una carpeta del servidor) |
| volumen `files_data` | Ficheros de la aplicación (PDFs) | **Sí** |

Ningún servicio publica puertos en el servidor: solo el proxy de HTTPS llega a `web`, y `web` a la API por la red interna de Docker. Las bases de datos, SuperTokens y Valkey no son alcanzables desde fuera aunque falle el cortafuegos.

Las tres piezas marcadas **Sí** son las que hay que [copiar](copias-de-seguridad.md). La base de datos de SuperTokens es tan importante como la de la aplicación: sin ella, nadie puede iniciar sesión.

## Qué es opcional

Con solo las [variables obligatorias](variables.md) la instalación arranca y se puede usar entera, excepto lo que necesita un servicio externo:

| Función | Sin configurarla | Cómo activarla |
|---|---|---|
| **Correo** | No se envía ningún email: ni avisos, ni recuperar la contraseña, ni confirmar el email (y entonces no se exige confirmarlo) | [Correo](correo.md) |
| **IA de la plataforma** (usos gratuitos) | Nadie tiene usos gratuitos; la IA solo funciona con la clave propia de cada usuario | [IA de la plataforma](ia-de-la-plataforma.md) |
| **Claves de IA propias** de los usuarios | No se ofrecen | `AI_KEYS_ENCRYPTION_KEYS` en las [variables](variables.md) |
| **Registro abierto** | Está cerrado: las cuentas las creas tú | [Cuentas](cuentas.md) |

## Pasos

1. Comprueba los [requisitos](requisitos.md).
2. Despliega [con Coolify](coolify.md) o [sin Coolify](sin-coolify.md), con las [variables](variables.md) preparadas.
3. Crea la [primera cuenta](cuentas.md).
4. Comprueba que las [copias de seguridad](copias-de-seguridad.md) se hacen y guarda aparte los secretos.
5. Opcional: configura el [correo](correo.md), la [IA de la plataforma](ia-de-la-plataforma.md) y el [despliegue continuo](despliegue-continuo.md).

Para [actualizar a una versión nueva](actualizar.md) no hay que ejecutar nada a mano.
