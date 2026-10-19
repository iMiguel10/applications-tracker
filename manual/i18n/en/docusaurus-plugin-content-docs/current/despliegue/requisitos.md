---
title: Server requirements
sidebar_label: Requirements
---

## Server

- **Docker** with **Docker Compose v2** (the `docker compose` command, no hyphen). If you use Coolify, it already comes with it.
- **Memory:** 2 GB as an indicative minimum and 4 GB recommended. The two databases, SuperTokens, the API, the `worker`, Valkey and Nginx fit in 2 GB with little margin; the `worker` asks for the most in peaks, when generating PDFs. **Building** the images on the server itself needs more memory than running them: the first build takes several minutes (about 7 in testing) and, if the server is tight, add swap in case it runs out of memory.
- **Disk:** a few GB for the images, plus whatever the data takes and room for at least two backups.
- **Outbound internet access** to download the images and, if you use them, to reach the SMTP server ([Email](correo.md)) and the AI provider.

You don't need to install Python, Node or PostgreSQL on the server: everything runs inside the containers.

## Domain and HTTPS

- A **domain** (or subdomain) whose `A` (or `AAAA`) DNS record points at the server. Any DNS provider works, including free ones such as DuckDNS.
- Server ports **80 and 443** open and reachable from the internet. The HTTPS proxy uses them: it gets the certificate from Let's Encrypt and needs to be reachable on 80 to validate it.
- The application needs **HTTPS**: session cookies are marked `Secure` and don't travel over `http://`. The only exception is trying it on `localhost`, see [Without Coolify](sin-coolify.md#trying-it-on-your-machine).

A single domain is enough: the web application, the manual and the API share an origin.

## Coolify

If you are going to use [Coolify](coolify.md): your own Coolify 4 installation (the recipe was tested with 4.4 and its Traefik proxy) with the server already added, and SSH access to the server for maintenance commands in case the panel's terminal doesn't work.

## With local AI

If you want Ollama for the free uses, it goes **outside** this deployment (another machine, preferably with a GPU, or a separate resource): `qwen3:8b` needs about 6 GB of memory plus context. It works without a GPU, but each proposal can take several minutes. See [Platform AI](ia-de-la-plataforma.md).
