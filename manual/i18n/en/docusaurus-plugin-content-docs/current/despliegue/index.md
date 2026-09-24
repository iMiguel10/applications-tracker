---
title: Deploying Applications Tracker
sidebar_label: Overview
---

Applications Tracker runs with **Docker Compose**: all its services are containers, and configuration goes in environment variables.

:::caution Status of this section
This covers what is the same in every installation: which services there are, how to configure them, how to connect email and how to back up. The production recipe (the production Compose file, the HTTPS proxy and publishing on a domain) will be added once it is ready. Until then, the repository only ships the development setup.
:::

## What is inside

| Service | What it does | Stores data? |
|---|---|---|
| `api` | The API (FastAPI). On start-up it **applies the database migrations by itself** | No |
| `worker` | Runs slow work in the background, such as sending emails or generating PDFs. It has no tasks yet, but it must be running | No |
| `frontend` | The web application | No |
| `db` | PostgreSQL with the application's data | **Yes** |
| `supertokens` | Authentication service (accounts and sessions) | No |
| `supertokens-db` | SuperTokens' own PostgreSQL: accounts and passwords | **Yes** |
| `valkey` | Queue of pending tasks | Only waiting tasks, no data |
| `files_data` volume | Application files (PDFs) | **Yes** |

The three pieces marked **Yes** are the ones to [back up](copias-de-seguridad.md). The SuperTokens database matters as much as the application's: without it, nobody can sign in.

## Steps

1. Check the [requirements](requisitos.md).
2. Prepare the [environment variables](variables.md).
3. If you want the application to send email, configure [email](correo.md).
4. Schedule [backups](copias-de-seguridad.md).

## Upgrading to a new version

When a new version starts, the `api` service applies pending migrations before accepting requests, so there is nothing to run by hand. **Back up before upgrading**: a migration does not undo itself.
