---
title: Desplegar Applications Tracker
sidebar_label: Visión general
---

Applications Tracker se ejecuta con **Docker Compose**: todos sus servicios son contenedores, y la configuración va en variables de entorno.

:::caution Estado de esta sección
Aquí está lo que es igual en cualquier instalación: qué servicios hay, cómo se configuran, cómo se conecta el correo y cómo se hacen copias de seguridad. La receta de producción (el fichero de Compose de producción, el proxy con HTTPS y la publicación en un dominio) se añadirá cuando esté lista. Hasta entonces, el repositorio solo trae la configuración de desarrollo.
:::

## Qué hay dentro

| Servicio | Qué hace | ¿Guarda datos? |
|---|---|---|
| `api` | La API (FastAPI). Al arrancar, **aplica sola las migraciones** de la base de datos | No |
| `worker` | Ejecuta en segundo plano las tareas lentas, como enviar emails o generar PDFs. Hoy todavía no tiene ninguna, pero debe estar en marcha | No |
| `frontend` | La aplicación web | No |
| `db` | PostgreSQL con los datos de la aplicación | **Sí** |
| `supertokens` | Servicio de autenticación (cuentas y sesiones) | No |
| `supertokens-db` | PostgreSQL propio de SuperTokens: cuentas y contraseñas | **Sí** |
| `valkey` | Cola de tareas pendientes | Solo tareas en espera, no datos |
| volumen `files_data` | Ficheros de la aplicación (PDFs) | **Sí** |

Las tres piezas marcadas **Sí** son las que hay que [copiar](copias-de-seguridad.md). La base de datos de SuperTokens es tan importante como la de la aplicación: sin ella, nadie puede iniciar sesión.

## Pasos

1. Comprueba los [requisitos](requisitos.md).
2. Prepara las [variables de entorno](variables.md).
3. Si quieres que la aplicación envíe emails, configura el [correo](correo.md).
4. Programa las [copias de seguridad](copias-de-seguridad.md).

## Actualizar a una versión nueva

Al arrancar una versión nueva, el servicio `api` aplica las migraciones pendientes antes de aceptar peticiones, así que no hay que ejecutar nada a mano. **Haz una copia de seguridad antes de actualizar**: una migración no se deshace sola.
