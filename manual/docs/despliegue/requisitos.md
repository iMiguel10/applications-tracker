---
title: Requisitos del servidor
sidebar_label: Requisitos
---

## Software

- **Docker** con **Docker Compose v2** (el comando `docker compose`, sin guion).
- Acceso de salida al servidor SMTP si vas a enviar emails (ver [Correo](correo.md)).

No hace falta instalar Python, Node ni PostgreSQL en el servidor: todo va dentro de los contenedores.

## Memoria y disco

| | Mínimo orientativo | Recomendado |
|---|---|---|
| Memoria | 2 GB | 4 GB |
| Disco | Unos pocos GB más lo que ocupen los datos | Espacio para al menos dos copias de seguridad |

Las dos bases de datos PostgreSQL, SuperTokens, la API, el worker y Valkey caben en 2 GB con poco margen. El worker es el que más memoria puede pedir en picos, al generar PDFs.

## Red

Solo hay que exponer la aplicación web y la API. **Nunca publiques** los puertos de las bases de datos, de SuperTokens ni de Valkey: solo los usan los demás contenedores por la red interna de Docker.
