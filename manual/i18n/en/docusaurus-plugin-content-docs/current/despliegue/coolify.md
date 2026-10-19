---
title: Deploying with Coolify
sidebar_label: With Coolify
---

Recipe tested with Coolify 4.4 (Traefik proxy) and a domain with Let's Encrypt HTTPS. Coolify downloads the repository, builds the images on your server, sets up HTTPS and hands the domain's traffic to the `web` service. Coolify's menu names may change between versions.

## Before you start

- You meet the [requirements](requisitos.md): Coolify running, a domain pointing at the server and ports 80 and 443 open.
- You have the [required variables](variables.md) ready, with their secrets already generated.

## 1. Create the resource

1. In your Coolify project, **+ New** and choose the Git repository (your own, if you forked it, or the project's public one).
2. As the build type (*Build Pack*), **Docker Compose**.
3. Branch `main`, *Base Directory* `/` and *Docker Compose Location* `/compose.prod.yml`.

Coolify reads the file and lists its services: `web`, `api`, `worker`, `db`, `supertokens-db`, `supertokens`, `valkey` and `backup`.

## 2. Assign the domain

The domain goes **only** on the `web` service, with `https://`:

```text
https://tracker.example.com
```

The other services get no domain. If you give one to another service, the proxy would publish internal services to the internet.

## 3. Variables

In the resource's *Environment Variables*, Coolify shows the ones the compose file mentions. Fill in at least the required ones (see [Variables](variables.md)):

| Variable | Value |
|---|---|
| `APP_URL` | The same domain, `https://tracker.example.com`, with no trailing slash |
| `POSTGRES_PASSWORD`, `SUPERTOKENS_DB_PASSWORD`, `SUPERTOKENS_API_KEY`, `APP_SECRET` | Four different values, generated with `openssl rand -hex 32` |

**Save these four secrets in a password manager now**: backups don't include them and you will need them to [restore](copias-de-seguridad.md).

If you want users to be able to use their own AI key, also generate and add `AI_KEYS_ENCRYPTION_KEYS` (see [Variables](variables.md)). You can leave email and platform AI for later.

## 4. First deployment

Click **Deploy**. The first time it builds the images on the server and takes a few minutes (about 7 in testing). If a required variable is missing, the deployment fails right away with its name in the log: add it and deploy again.

**What you should see:** the eight services running (*Running*) and, after a minute, no *unhealthy* warnings. Coolify requests the certificate the first time the domain receives traffic.

## 5. Check it

```bash
curl https://tracker.example.com/api/v1/health
```

It must answer `{"status":"ok","database":"ok","environment":"production"}`. In the browser, `https://tracker.example.com` shows the sign-in page (with the certificate padlock) and `https://tracker.example.com/manual/` shows this manual.

If `health` fails in the first minute, the API is still applying migrations: wait and try again.

## 6. Create the first account

Sign-up comes closed. Create your account with [the accounts script](cuentas.md); it is the last step before you can sign in.

## Maintenance commands

Some steps (creating accounts, a manual backup, restoring) run inside a container. There are two ways:

- **Coolify's terminal:** in the resource, open the service's terminal (`api`, `backup`…).
- **Over SSH, with Docker**, if the panel's terminal doesn't work. Containers are named `<service>-<uuid>-<date>`; find them with:

    ```bash
    docker ps --format '{{.Names}}' | grep api
    docker exec -it <api-container> python -m app.scripts.create_user ana@example.com
    ```

The container name **changes with every deployment**: look it up again.

## Next steps

- [Email](correo.md) and [Platform AI](ia-de-la-plataforma.md), when you want them.
- [Continuous deployment](despliegue-continuo.md): every new version deploys itself after passing the CI.
- [Backups](copias-de-seguridad.md): check that the first one succeeds.
