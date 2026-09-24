---
title: Server requirements
sidebar_label: Requirements
---

## Software

- **Docker** with **Docker Compose v2** (the `docker compose` command, no hyphen).
- Outbound access to the SMTP server if you are going to send email (see [Email](correo.md)).

You don't need Python, Node or PostgreSQL installed on the server: everything runs inside the containers.

## Memory and disk

| | Rough minimum | Recommended |
|---|---|---|
| Memory | 2 GB | 4 GB |
| Disk | A few GB plus the size of the data | Room for at least two backups |

The two PostgreSQL databases, SuperTokens, the API, the worker and Valkey fit in 2 GB with little headroom. The worker is the one that may need the most memory at peaks, when generating PDFs.

## Network

Only the web application and the API need to be exposed. **Never publish** the ports of the databases, SuperTokens or Valkey: only the other containers use them, over Docker's internal network.
