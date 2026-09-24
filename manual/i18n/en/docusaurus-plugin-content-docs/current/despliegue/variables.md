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

## Environment

| Variable | Required | What it is |
|---|---|---|
| `ENV` | Yes | `development` or `production`. In `development`, the API logs every SQL query |
