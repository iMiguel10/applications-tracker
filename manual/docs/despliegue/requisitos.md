---
title: Requisitos del servidor
sidebar_label: Requisitos
---

## Servidor

- **Docker** con **Docker Compose v2** (el comando `docker compose`, sin guion). Si usas Coolify, ya viene con él.
- **Memoria:** 2 GB como mínimo orientativo y 4 GB recomendados. Las dos bases de datos, SuperTokens, la API, el `worker`, Valkey y Nginx caben en 2 GB con poco margen; el `worker` es el que más pide en picos, al generar PDFs. **Construir** las imágenes en el propio servidor necesita más memoria que ejecutarlas: la primera construcción tarda varios minutos (unos 7 en las pruebas) y, si el servidor va justo, añade memoria de intercambio (swap) por si se queda sin memoria.
- **Disco:** unos pocos GB para las imágenes, más lo que ocupen los datos y espacio para al menos dos copias de seguridad.
- **Salida a internet** para descargar las imágenes y, si los usas, para el servidor SMTP ([Correo](correo.md)) y el proveedor de IA.

No hace falta instalar Python, Node ni PostgreSQL en el servidor: todo va dentro de los contenedores.

## Dominio y HTTPS

- Un **dominio** (o subdominio) cuyo registro DNS `A` (o `AAAA`) apunte al servidor. Sirve cualquier proveedor de DNS, incluidos los gratuitos como DuckDNS.
- Los puertos **80 y 443** del servidor abiertos y alcanzables desde internet. Los usa el proxy de HTTPS, que obtiene el certificado de Let's Encrypt y necesita llegar por el 80 para validarlo.
- La aplicación necesita **HTTPS**: las cookies de sesión se marcan `Secure` y no viajan por `http://`. La única excepción es probarla en `localhost`, ver [Sin Coolify](sin-coolify.md#probarlo-en-tu-maquina).

Un solo dominio basta: la aplicación web, el manual y la API comparten origen.

## Coolify

Si vas a usar [Coolify](coolify.md): una instalación propia de Coolify 4 (la receta se probó con la 4.4 y su proxy Traefik) con el servidor ya añadido, y acceso por SSH al servidor para los comandos de mantenimiento si la terminal del panel no funciona.

## Con IA local

Si quieres Ollama para los usos gratuitos, va **fuera** de este despliegue (otra máquina, preferiblemente con GPU, o un recurso aparte): `qwen3:8b` necesita unos 6 GB de memoria más el contexto. Sin GPU funciona, pero cada propuesta puede tardar varios minutos. Ver [IA de la plataforma](ia-de-la-plataforma.md).
