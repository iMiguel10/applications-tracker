---
title: Deploying without Coolify
sidebar_label: Without Coolify
---

`compose.prod.yml` doesn't depend on Coolify: it works on any server with Docker, as long as you put in front a proxy that terminates HTTPS and passes **all** the domain's traffic to the `web` service (port 80). Nginx, Caddy and Traefik all work.

## 1. Prepare the variables

Download the repository and create the variables file next to `compose.prod.yml`:

```bash
git clone https://github.com/iMiguel10/applications-tracker.git && cd applications-tracker
cp .env.prod.example .env
```

Edit `.env`: set `APP_URL` and the four secrets (see [Variables](variables.md); `openssl rand -hex 32` generates them). Save the secrets somewhere else.

## 2. Start it

```bash
docker compose -f compose.prod.yml up -d --build
```

**What you should see:** `docker compose -f compose.prod.yml ps` lists eight services, with the databases, `api`, `supertokens` and `valkey` as `healthy` (the first build takes several minutes).

If a required variable is missing, the command fails before starting anything and says which one.

## 3. Put the proxy in front

`compose.prod.yml` publishes no ports. There are two ways for the proxy to reach `web`:

- **Proxy in the same Docker:** connect it to the project's network (`docker network ls`; it is called `<folder>_default`) and point it at `web:80`.
- **Proxy on the server (outside Docker):** add a `compose.override.yml` file that publishes `web` only on the server itself and point the proxy at that port:

    ```yaml
    services:
      web:
        ports:
          - "127.0.0.1:8080:80"
    ```

    And start with `-f compose.prod.yml -f compose.override.yml`.

:::danger Don't publish the API or the databases
The application trusts the `X-Forwarded-For` headers coming from private networks, because only containers reach the API. If you published the API's port on the server, anyone on your network could invent their IP and skip the request limit. Publish only `web`.
:::

:::warning Publish `web` only on `127.0.0.1`, never on every interface
Nginx also trusts the `X-Forwarded-For` that arrives from private networks. With `"8080:80"` (without `127.0.0.1:`), any machine on your local network could connect straight to `web`, invent its IP and skip the request limit. And the server's proxy must **replace** the client's `X-Forwarded-For` or **append** the real IP to it, never pass it through unchanged.
:::

The proxy must send `X-Forwarded-For` and `X-Forwarded-Proto` (almost all do by default). With a tunnel in front of the proxy (such as Cloudflare Tunnel), check that the IP the application sees is the visitor's and not the tunnel's.

## 4. Check it and create the account

```bash
curl https://tracker.example.com/api/v1/health
```

It must answer `{"status":"ok","database":"ok","environment":"production"}`. Then create the [first account](cuentas.md), with `docker compose -f compose.prod.yml exec api …`.

To change a variable later (email, AI), edit `.env` and repeat `docker compose -f compose.prod.yml up -d --build`: Docker recreates only the services that change.

## Trying it on your machine

To see the whole production setup on your computer, with no domain or HTTPS, the repository ships `compose.prod.local.yml`, which publishes `web` on `127.0.0.1:8088`:

1. Create a `.env.prod.local` from `.env.prod.example`, with `APP_URL=http://localhost:8088` (with `localhost`, never `127.0.0.1`) and any values for the secrets.
2. Start it:

    ```bash
    docker compose -p at-prod --env-file .env.prod.local -f compose.prod.yml -f compose.prod.local.yml up -d --build
    ```

3. Open `http://localhost:8088`. To create an account: `docker compose -p at-prod -f compose.prod.yml exec api python -m app.scripts.create_user you@email.com`.
4. When you are done, `docker compose -p at-prod down -v` deletes everything, data included.

It is for testing only: no HTTPS, and with backups saved in `/var/backups/applications-tracker` on your machine (or the folder you set in `BACKUP_HOST_DIR`).
