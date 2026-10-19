---
title: Desplegar sin Coolify
sidebar_label: Sin Coolify
---

`compose.prod.yml` no depende de Coolify: sirve en cualquier servidor con Docker, siempre que pongas delante un proxy que termine el HTTPS y le pase **todo** el tráfico del dominio al servicio `web` (puerto 80). Nginx, Caddy y Traefik valen.

## 1. Preparar las variables

Descarga el repositorio y crea el fichero de variables junto a `compose.prod.yml`:

```bash
git clone https://github.com/iMiguel10/applications-tracker.git && cd applications-tracker
cp .env.prod.example .env
```

Edita `.env`: pon `APP_URL` y los cuatro secretos (ver [Variables](variables.md); `openssl rand -hex 32` los genera). Guarda los secretos aparte.

## 2. Arrancar

```bash
docker compose -f compose.prod.yml up -d --build
```

**Qué debe verse:** `docker compose -f compose.prod.yml ps` lista ocho servicios, con las bases de datos, `api`, `supertokens` y `valkey` como `healthy` (la primera construcción tarda varios minutos).

Si falta una variable obligatoria, el comando falla antes de arrancar nada y dice cuál.

## 3. Poner el proxy delante

`compose.prod.yml` no publica ningún puerto. Hay dos formas de que el proxy llegue a `web`:

- **Proxy en el mismo Docker:** conéctalo a la red del proyecto (`docker network ls`; se llama `<carpeta>_default`) y apunta a `web:80`.
- **Proxy en el servidor (fuera de Docker):** añade un fichero `compose.override.yml` que publique `web` solo en el propio servidor y apunta el proxy a ese puerto:

    ```yaml
    services:
      web:
        ports:
          - "127.0.0.1:8080:80"
    ```

    Y arranca con `-f compose.prod.yml -f compose.override.yml`.

:::danger No publiques la API ni las bases de datos
La aplicación se fía de las cabeceras `X-Forwarded-For` que lleguen desde las redes privadas, porque a la API solo llegan contenedores. Si publicaras el puerto de la API en el servidor, cualquiera de tu red podría inventarse su IP y saltarse el límite de peticiones. Publica únicamente `web`.
:::

:::warning Publica `web` solo en `127.0.0.1`, nunca en todas las interfaces
Nginx también se fía del `X-Forwarded-For` que llega desde las redes privadas. Con `"8080:80"` (sin `127.0.0.1:`), cualquier equipo de tu red local podría conectarse directamente a `web`, inventarse su IP y saltarse el límite de peticiones. Y el proxy del servidor debe **sustituir** o **añadir al final** el `X-Forwarded-For` del cliente, nunca pasarlo tal cual sin añadir la IP real.
:::

El proxy debe enviar `X-Forwarded-For` y `X-Forwarded-Proto` (casi todos lo hacen por defecto). Con un túnel delante del proxy (como Cloudflare Tunnel), comprueba que la IP que ve la aplicación es la del visitante y no la del túnel.

## 4. Comprobar y crear la cuenta

```bash
curl https://tracker.example.com/api/v1/health
```

Debe responder `{"status":"ok","database":"ok","environment":"production"}`. Después, crea la [primera cuenta](cuentas.md), con `docker compose -f compose.prod.yml exec api …`.

Para cambiar una variable más adelante (correo, IA), edita `.env` y repite `docker compose -f compose.prod.yml up -d --build`: Docker recrea solo los servicios que cambian.

## Probarlo en tu máquina {#probarlo-en-tu-maquina}

Para ver la producción entera en tu ordenador, sin dominio ni HTTPS, el repositorio trae `compose.prod.local.yml`, que publica `web` en `127.0.0.1:8088`:

1. Crea un `.env.prod.local` a partir de `.env.prod.example`, con `APP_URL=http://localhost:8088` (con `localhost`, nunca `127.0.0.1`) y los secretos con cualquier valor.
2. Arranca:

    ```bash
    docker compose -p at-prod --env-file .env.prod.local -f compose.prod.yml -f compose.prod.local.yml up -d --build
    ```

3. Abre `http://localhost:8088`. Para crear una cuenta: `docker compose -p at-prod -f compose.prod.yml exec api python -m app.scripts.create_user tu@email.com`.
4. Al terminar, `docker compose -p at-prod down -v` lo borra todo, datos incluidos.

Es solo para probar: sin HTTPS, y con las copias de seguridad guardándose en `/var/backups/applications-tracker` de tu equipo (o en la carpeta que pongas en `BACKUP_HOST_DIR`).
