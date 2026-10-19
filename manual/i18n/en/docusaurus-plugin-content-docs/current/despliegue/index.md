---
title: Deploying Applications Tracker
sidebar_label: Overview
---

Applications Tracker is deployed with **Docker Compose**: all its services are containers and configuration goes in environment variables. The repository ships the production file, `compose.prod.yml`, and there are two tested ways to use it:

- [**With Coolify**](coolify.md): it builds on your server, sets up HTTPS and can deploy every new version from the CI. This is the reference recipe.
- [**Without Coolify**](sin-coolify.md): `docker compose` and any HTTPS proxy in front.

## What gets deployed

A single domain serves the web application, the manual and the API. The `web` service (an Nginx) is the only one that receives traffic: the HTTPS proxy hands it the whole domain and it routes requests.

| Service | What it does | Stores data? |
|---|---|---|
| `web` | Serves the web application and this manual (at `/manual/`), and routes `/api/` and `/auth/` to the API. It limits requests per IP and sets the security headers | No |
| `api` | The API (FastAPI). On start-up it **applies the database migrations by itself** | No |
| `worker` | Runs slow work in the background: sending emails, generating PDFs, calling the AI and scheduling notifications. It must be running | No |
| `db` | PostgreSQL with the application's data | **Yes** |
| `supertokens` | Authentication service (accounts and sessions) | No |
| `supertokens-db` | SuperTokens' own PostgreSQL: accounts and passwords | **Yes** |
| `valkey` | Queue of pending tasks and request-limit counters | Only waiting tasks, no data |
| `backup` | Backs up both databases and the files every night. See [Backups](copias-de-seguridad.md) | The backups (in a folder on the server) |
| `files_data` volume | Application files (PDFs) | **Yes** |

No service publishes ports on the server: only the HTTPS proxy reaches `web`, and `web` reaches the API over Docker's internal network. The databases, SuperTokens and Valkey are not reachable from outside even if the firewall fails.

The three pieces marked **Yes** are the ones to [back up](copias-de-seguridad.md). The SuperTokens database matters as much as the application's: without it, nobody can sign in.

## What is optional

With only the [required variables](variables.md) the installation starts and can be fully used, except for what needs an external service:

| Feature | If not configured | How to enable it |
|---|---|---|
| **Email** | No email is sent: no notifications, no password recovery, no email confirmation (and then confirming is not required) | [Email](correo.md) |
| **Platform AI** (free uses) | Nobody gets free uses; AI only works with each user's own key | [Platform AI](ia-de-la-plataforma.md) |
| **Users' own AI keys** | Not offered | `AI_KEYS_ENCRYPTION_KEYS` in the [variables](variables.md) |
| **Open sign-up** | It is closed: you create the accounts | [Accounts](cuentas.md) |

## Steps

1. Check the [requirements](requisitos.md).
2. Deploy [with Coolify](coolify.md) or [without Coolify](sin-coolify.md), with the [variables](variables.md) ready.
3. Create the [first account](cuentas.md).
4. Check that [backups](copias-de-seguridad.md) are being made and keep the secrets somewhere else.
5. Optional: set up [email](correo.md), [platform AI](ia-de-la-plataforma.md) and [continuous deployment](despliegue-continuo.md).

To [upgrade to a new version](actualizar.md) there is nothing to run by hand.
