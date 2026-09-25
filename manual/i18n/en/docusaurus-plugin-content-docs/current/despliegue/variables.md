---
title: Environment variables
sidebar_label: Environment variables
---

All configuration goes in a `.env` file at the project root. The repository ships a template, `.env.example`, with development values:

```bash
cp .env.example .env
```

:::danger Before exposing the installation
Change **every** password and the SuperTokens key to long random values, and never commit the `.env` to a repository. For example, to generate a value:

```bash
openssl rand -hex 32
```
:::

A new value in `.env` is not picked up by a plain restart: the container reads the file when it is **created**. After changing it:

```bash
docker compose up -d --force-recreate
```

## Application database

| Variable | Required | What it is |
|---|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Yes | Database, user and password that the `db` container creates the first time it starts |
| `DATABASE_URL` | Yes | How the API connects: `postgresql+asyncpg://USER:PASSWORD@db:5432/DATABASE`, with the same values as above |

## Authentication (SuperTokens)

| Variable | Required | What it is |
|---|---|---|
| `SUPERTOKENS_DB_NAME`, `SUPERTOKENS_DB_USER`, `SUPERTOKENS_DB_PASSWORD` | Yes | SuperTokens' own database |
| `SUPERTOKENS_CONNECTION_URI` | Yes | Internal address of the service: `http://supertokens:3567` |
| `SUPERTOKENS_API_KEY` | Yes | Key shared between the API and SuperTokens, **at least 20 characters long** |
| `API_DOMAIN` | Yes | Public URL of the API, for example `https://api.yourdomain.com` |
| `WEBSITE_DOMAIN` | Yes | Public URL of the web application, for example `https://yourdomain.com` |

`WEBSITE_DOMAIN` is also the start of the **links in emails** (password recovery): in production it must be the public address, never the development one.

`API_DOMAIN` and `WEBSITE_DOMAIN` decide which site the session cookies belong to. They must match **exactly** the addresses users type in the browser: `localhost` and `127.0.0.1` are different sites for a browser, and if they don't match, signing in seems not to work, without any error.

## Web application

| Variable | Required | What it is |
|---|---|---|
| `CORS_ORIGINS` | Yes | Origins allowed to call the API from a browser, comma-separated. Usually the same value as `WEBSITE_DOMAIN` |
| `VITE_API_URL` | Yes | API URL used by the web application. Usually the same value as `API_DOMAIN` |

## Task queue and files

| Variable | Required | What it is |
|---|---|---|
| `VALKEY_URL` | Yes | Valkey address: `redis://valkey:6379/0` |
| `FILES_ROOT` | Yes | Folder for files inside the containers: `/data/files` (the `files_data` volume) |

If either of these is missing, the API does not start.

## Email

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_TIMEOUT_SECONDS` and `EMAIL_FROM`. They are optional: without `SMTP_HOST`, the application starts anyway and sends no email. See [Email](correo.md).

## Per-account limits

| Variable | Default | What it limits |
|---|---|---|
| `LIMIT_APPLICATIONS` | 5000 | Applications per account, archived ones included |
| `LIMIT_COMPANIES` | 2000 | Companies per account |
| `LIMIT_REMINDERS` | 5000 | Reminders per account, in any status |

They are optional and apply to every account. To give a single account a different value, without touching the others:

```bash
docker compose exec api python -m app.scripts.set_user_limit ana@example.com                       # see its usage and limits
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications 10000    # exception for that account
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --unlimited  # no limit
docker compose exec api python -m app.scripts.set_user_limit ana@example.com all --unlimited         # no limit on everything that allows it
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --reset  # back to the global value (all --reset, every one)
```

Lowering a limit below what the account already has deletes nothing: it only stops it from creating more. An account with no limit sees in Preferences how much it has used and "no limit", and never gets warnings.

## Request limits

| Variable | Default | What it is |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Limits sign-in, sign-up and email attempts, and each user's requests. Only turned off for tests |
| `TRUSTED_PROXIES` | empty | IPs or networks (CIDR) of your proxies, comma-separated, for example `172.18.0.0/16` |

:::warning Behind a proxy, TRUSTED_PROXIES is required
If the application is behind a proxy (Nginx, a load balancer), every request reaches it from the proxy's IP. Without `TRUSTED_PROXIES`, all users share that IP and the limit of 10 sign-ins per minute is split among everyone. With it, the application reads the real IP from the `X-Forwarded-For` header, but only when a proxy on the list sets it.
:::

Limits are kept in Valkey. If Valkey doesn't respond, the application lets requests through without limits and logs it, so that nobody is locked out.

## Environment

| Variable | Required | What it is |
|---|---|---|
| `ENV` | Yes | `development` or `production`. In `development`, the API logs every SQL query |
