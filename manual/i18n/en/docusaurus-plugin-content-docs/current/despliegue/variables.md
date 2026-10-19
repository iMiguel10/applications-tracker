---
title: Environment variables
sidebar_label: Environment variables
---

Production configuration is a handful of variables. In **Coolify** they go in the resource's *Environment Variables*; **without Coolify**, in a `.env` file next to `compose.prod.yml`. The repository ships the template, `.env.prod.example`, with every variable explained:

```bash
cp .env.prod.example .env
```

Changing a variable requires **deploying again** (in Coolify, **Deploy**; without it, `docker compose -f compose.prod.yml up -d --build`). A restart is not enough: the container reads its variables when it is created. `APP_URL` also rebuilds the `web` image, which carries it inside.

:::danger Secrets
Generate every password and key **different**, long and random, for example with `openssl rand -hex 32`. Don't commit them to a repository and keep them in a password manager: [backups](copias-de-seguridad.md) don't include them.
:::

If a required variable is missing, the deployment fails before starting anything and the message says which one.

## Required

| Variable | What it is |
|---|---|
| `APP_URL` | Public address of the application, with `https://` and **no trailing slash**: `https://tracker.example.com`. It is the web, the API and the start of the links in emails. It must match **exactly** what users type in the browser, because the session cookies depend on it |
| `POSTGRES_PASSWORD` | Password of the application database |
| `SUPERTOKENS_DB_PASSWORD` | Password of the SuperTokens database |
| `SUPERTOKENS_API_KEY` | Key shared between the API and SuperTokens, at least 20 characters |
| `APP_SECRET` | Secret of at least 32 characters used to sign the unsubscribe links of notification emails. If you change it, the unsubscribe links in emails already sent stop working (users can still change their notifications in Preferences) |

Changing `POSTGRES_PASSWORD` or `SUPERTOKENS_DB_PASSWORD` **after the first start** doesn't change the password inside the database, which was set when it was created: the application would stop connecting. Choose them well from the start.

## Sign-up

| Variable | Default | What it is |
|---|---|---|
| `SIGNUP_ENABLED` | `false` | With `false`, nobody can create an account: the sign-in page doesn't offer it and the sign-up page says it is closed. You create the accounts ([Accounts](cuentas.md)). With `true`, anyone can sign up |

## Users' own AI keys

| Variable | Default | What it is |
|---|---|---|
| `AI_KEYS_ENCRYPTION_KEYS` | empty | Master keys that encrypt the API keys users store, separated by commas, the newest first. Empty: users can't use their own key |
| `AI_ANTHROPIC_MODELS` | those in `compose.prod.yml` | Models a user can choose with their Anthropic key, separated by commas; the first one is the recommended one. Empty: Anthropic is not offered |
| `AI_OPENAI_MODELS` | those in `compose.prod.yml` | The same for OpenAI |
| `AI_GROQ_MODELS` | those in `compose.prod.yml` | The same for Groq |

To generate a master key, from the `api` service's terminal (or with `docker exec -it <api-container> …`):

```bash
python -m app.scripts.rotate_ai_keys --new-key
```

It prints a new key; copy it into `AI_KEYS_ENCRYPTION_KEYS`. If you remove from the list a model someone is using, their key is kept and they are asked to choose another.

:::danger Keep the master key somewhere else
Without it, the keys users stored can't be decrypted and they would have to enter them again. Keep it **outside** the database backups: with both, anyone could read the keys.
:::

To change it without anyone losing theirs: put the new one **first** in `AI_KEYS_ENCRYPTION_KEYS` without removing the old one, deploy again, run `python -m app.scripts.rotate_ai_keys` in the `api` service and then remove the old one and deploy once more.

## Email

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` and `SMTP_TIMEOUT_SECONDS` (seconds to wait for each send, 30 by default). Optional: without `SMTP_HOST`, the application starts anyway and doesn't send emails. See [Email](correo.md).

## Platform AI

`AI_PLATFORM_PROVIDER`, `AI_PLATFORM_MODEL`, `AI_PLATFORM_API_KEY`, `AI_PLATFORM_INPUT_USD_PER_MTOK`, `AI_PLATFORM_OUTPUT_USD_PER_MTOK`, `AI_OLLAMA_BASE_URL`, `AI_OLLAMA_CONTEXT_TOKENS`, `AI_REQUEST_TIMEOUT_SECONDS`, `LIMIT_AI_CV_PROPOSALS` and `LIMIT_AI_COVER_LETTER_PROPOSALS`. Optional: without `AI_PLATFORM_PROVIDER` there are no free uses. Each one is explained in [Platform AI](ia-de-la-plataforma.md).

## Per-account limits

| Variable | Default | What it limits |
|---|---|---|
| `LIMIT_APPLICATIONS` | 5000 | Applications per account, archived included |
| `LIMIT_COMPANIES` | 2000 | Companies per account |
| `LIMIT_REMINDERS` | 5000 | Reminders per account, in any state |
| `LIMIT_DOCUMENTS` | 100 | Documents (CVs and letters) per account, archived included |
| `LIMIT_STORAGE_BYTES` | 104857600 (100 MB) | Storage per account, **in bytes**: the sum of its documents, archived included |
| `DOCUMENT_MAX_BYTES` | 5242880 (5 MB) | Maximum size of each uploaded PDF, in bytes. Not per account: it applies to all. The web server accepts bodies of up to 25 MB, so don't set more |

They are optional and apply to every account. To give a specific account another value, without touching the others, run in the `api` service (through Coolify's terminal or with `docker exec -it <api-container>`; without Coolify, `docker compose -f compose.prod.yml exec api`):

```bash
python -m app.scripts.set_user_limit ana@example.com                          # see its usage and limits
python -m app.scripts.set_user_limit ana@example.com applications 10000       # exception for that account
python -m app.scripts.set_user_limit ana@example.com applications --unlimited # no limit
python -m app.scripts.set_user_limit ana@example.com all --unlimited          # no limit on everything that allows it
python -m app.scripts.set_user_limit ana@example.com applications --reset     # back to the global value (all --reset, all of them)
```

Storage is also in bytes in the script (`storage_bytes 524288000` is 500 MB) and is the only one that **doesn't allow** `--unlimited`: disk costs money, and an account with no cap could fill it. `all --unlimited` leaves it as it is.

Lowering a limit below what the account already has deletes nothing: it only stops it from creating more. An account with no limit sees in Preferences how much it has and "no limit", and never gets warnings.

## Database

| Variable | Default | What it is |
|---|---|---|
| `POSTGRES_DB` | `applications_tracker` | Name of the application database |
| `POSTGRES_USER` | `applications_tracker` | Its user |

Like the passwords, they are only set when the database is created: don't change them on an installation that already has data.

## Backups

`BACKUP_HOST_DIR`, `TZ`, `BACKUP_SCHEDULE`, `BACKUP_KEEP_DAILY`, `BACKUP_KEEP_WEEKLY`, `BACKUP_MAX_AGE_HOURS` and `BACKUP_RCLONE_REMOTE`. All optional, explained in [Backups](copias-de-seguridad.md).

## Request limit and proxies

The request limit (10 sign-in attempts per minute per IP, 600 requests per minute per user…) is on and **not configurable**: the web server applies the first layer per IP and the API the second per IP, email and user. You don't need to touch `TRUSTED_PROXIES` either: `compose.prod.yml` sets it to the private networks, because only containers reach the API. That is why you must not publish the API's port (see [Without Coolify](sin-coolify.md)).

The limits are stored in Valkey. If Valkey doesn't respond, the application lets requests through without limit and logs it, so that nobody is locked out. While it is down it tries again every 30 seconds, and the limits come back by themselves as soon as Valkey responds.
