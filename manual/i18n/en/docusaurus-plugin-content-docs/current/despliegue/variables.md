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

## Sign-up

| Variable | Default | What it is |
|---|---|---|
| `SIGNUP_ENABLED` | `true` | With `false`, nobody can create an account: the sign-in screen doesn't offer it and the sign-up page says it is closed. Existing accounts work as before |

With sign-up closed, you create the accounts:

```bash
docker compose exec api python -m app.scripts.create_user ana@example.com
docker compose exec api python -m app.scripts.create_user ana@example.com --language en   # account and email in English
```

The account is created with the email already verified and a random password nobody knows. The person chooses theirs with a link: if the installation sends email, they get one ("Your Applications Tracker account is ready"); if not, or if sending fails, the script prints it for you to pass on. The link expires in 60 minutes. If it expires, they can ask for another one with **Forgot your password?**, as long as the installation sends email; without email, delete the account and create it again.

The script also works with sign-up open, and does nothing if an account with that email already exists.

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

## Signed links

| Variable | Required | What it is |
|---|---|---|
| `APP_SECRET` | Yes | A secret of at least 32 characters used to sign the unsubscribe links of email notifications. Generate a random one, for example with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

If it is missing or shorter, the API does not start. Keep it like any other password: anyone who knows it can unsubscribe any user from notifications. If you change it, the unsubscribe links in emails already sent stop working (users can still change their notifications in Preferences).

## Email

`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_TIMEOUT_SECONDS` and `EMAIL_FROM`. They are optional: without `SMTP_HOST`, the application starts anyway and sends no email. See [Email](correo.md).

## Per-account limits

| Variable | Default | What it limits |
|---|---|---|
| `LIMIT_APPLICATIONS` | 5000 | Applications per account, archived ones included |
| `LIMIT_COMPANIES` | 2000 | Companies per account |
| `LIMIT_REMINDERS` | 5000 | Reminders per account, in any status |
| `LIMIT_DOCUMENTS` | 100 | Documents (CVs and cover letters) per account, archived ones included |
| `LIMIT_STORAGE_BYTES` | 104857600 (100 MB) | Storage per account, **in bytes**: the sum of its documents, archived ones included |
| `DOCUMENT_MAX_BYTES` | 5242880 (5 MB) | Maximum size of each uploaded PDF, in bytes. Not per account: it applies to all |

They are optional and apply to every account. To give a single account a different value, without touching the others:

```bash
docker compose exec api python -m app.scripts.set_user_limit ana@example.com                       # see its usage and limits
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications 10000    # exception for that account
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --unlimited  # no limit
docker compose exec api python -m app.scripts.set_user_limit ana@example.com all --unlimited         # no limit on everything that allows it
docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --reset  # back to the global value (all --reset, every one)
```

Storage is also in bytes in the script (`storage_bytes 524288000` is 500 MB), and it is the only one that **does not allow** `--unlimited`: disk space costs money, and an account with no cap could fill it. `all --unlimited` leaves it as it is.

Lowering a limit below what the account already has deletes nothing: it only stops it from creating more. An account with no limit sees in Preferences how much it has used and "no limit", and never gets warnings.

## Artificial intelligence

The AI tailors a CV or writes a cover letter for a job. There are two ways to use it: the installation's **free uses**, with its provider and model, and each user's **own key**.

| Variable | Default | What it is |
|---|---|---|
| `AI_PLATFORM_PROVIDER` | empty | Provider for the free uses: `groq`, `anthropic`, `openai` or `ollama`. Empty: no free use |
| `AI_PLATFORM_MODEL` | empty | Model of that provider, for example `openai/gpt-oss-120b` on Groq |
| `AI_PLATFORM_API_KEY` | empty | The installation's API key for that provider. Not needed with Ollama |
| `AI_OLLAMA_BASE_URL` | empty | Address of your Ollama, for example `http://ollama:11434`. Required with `AI_PLATFORM_PROVIDER=ollama` |
| `AI_PLATFORM_INPUT_USD_PER_MTOK` | 0 | Model price per million input tokens, in dollars. Only used to estimate the cost of each use |
| `AI_PLATFORM_OUTPUT_USD_PER_MTOK` | 0 | The same for output tokens |
| `AI_OLLAMA_CONTEXT_TOKENS` | 16384 | Context tokens requested from Ollama, input and output together. More context, more memory |
| `AI_REQUEST_TIMEOUT_SECONDS` | 120 | Maximum time to wait for an answer from the provider. With a local model, raise it (300) |
| `LIMIT_AI_CV_PROPOSALS` | 1 | Free uses to tailor the CV, per account. They don't renew. `unlimited`: no cap |
| `LIMIT_AI_COVER_LETTER_PROPOSALS` | 1 | The same for cover letters |
| `AI_KEYS_ENCRYPTION_KEYS` | empty | Master keys that encrypt users' keys, comma-separated with the new one first. Empty: users can't use their own key |
| `AI_ANTHROPIC_MODELS` | empty | Models a user can choose with their Anthropic key, comma-separated; the first one is the recommended one. Empty: Anthropic isn't offered |
| `AI_OPENAI_MODELS` | empty | The same for OpenAI |
| `AI_GROQ_MODELS` | empty | The same for Groq |

If you set `AI_PLATFORM_PROVIDER`, the model and the key (with Ollama, its address) are required: without them, the API does not start. To check they work, with a real call that costs a few dozen tokens:

```bash
docker compose exec api python -m app.scripts.check_ai_provider
```

Keep the key like any other password: whoever has it spends on your provider account. Also set a spending cap in the provider's console.

:::warning Free uses with no cap
`unlimited` removes the cap for every account. With your own Ollama it costs nothing per use; with a paid provider, **spending has no limit**. You can still give one account a number with `set_user_limit` (for example, `ai_cv_proposals 5`), but not leave it without a cap.
:::

### Free uses with your own Ollama

With [Ollama](https://ollama.com) on your server, the free uses cost you nothing per use. It is what the `.env.example` template comes with, with an `ollama` container and the `qwen3:8b` model. Download the model first, just once:

```bash
docker compose exec ollama ollama pull qwen3:8b
```

And set:

```bash
AI_PLATFORM_PROVIDER=ollama
AI_PLATFORM_MODEL=qwen3:8b
AI_OLLAMA_BASE_URL=http://ollama:11434
AI_REQUEST_TIMEOUT_SECONDS=300
```

From the containers, an Ollama installed on the same machine is `http://host.docker.internal:11434`. A small model answers worse and takes longer: check the result with `check_ai_provider`. With an NVIDIA GPU, Ollama is much faster: in the development environment, start it with `docker compose -f compose.yml -f compose.gpu.yml up -d ollama`.

### Users' own keys

To let each user use their own Anthropic, OpenAI or Groq key (no usage limit, at their own cost), generate a master key and put it in `AI_KEYS_ENCRYPTION_KEYS`:

```bash
docker compose exec api python -m app.scripts.rotate_ai_keys --new-key
```

Then choose each provider's models in `AI_ANTHROPIC_MODELS`, `AI_OPENAI_MODELS` and `AI_GROQ_MODELS`. A provider without models isn't offered. If you remove from the list a model someone uses, their key is kept and they are asked to choose another.

:::danger Keep the master key with your backup
Without it, users' keys can't be decrypted: they would have to save them again. Keep it apart from the database backup: with both, anyone could read the keys.
:::

To change the master key without anyone losing theirs: put the new one **first** in `AI_KEYS_ENCRYPTION_KEYS` without removing the old one, recreate `api` and `worker`, run `docker compose exec api python -m app.scripts.rotate_ai_keys` and then remove the old one.

### Evaluate a model before offering it

Not every model answers equally well: some invent more, embellish more or break the answer format, and then the user spends a use and gets nothing. Before you put a model in `AI_PLATFORM_MODEL` or in an `AI_*_MODELS` list, try it with the evaluation that comes with the application. It runs a few sample profiles and job offers (made up) through each model, with the same prompt and the same check as the application:

```bash
docker compose exec api python -m evals.ai.run --target ollama:qwen3:8b --runs 2
```

With a paid provider, pass its key only for that run and confirm with `--yes`, because each call costs money:

```bash
docker compose exec -e EVAL_ANTHROPIC_API_KEY=your-key api python -m evals.ai.run --target anthropic:claude-sonnet-5-5 --yes
```

When it finishes it shows a table with how many proposals worked for each model and task, and leaves a report with all the texts in `backend/evals/ai/results/` for you to read: the automatic check guarantees the model doesn't invent experience, not that it writes well.

## Request limits

| Variable | Default | What it is |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Limits sign-in, sign-up and email attempts, and each user's requests. Only turned off for tests |
| `TRUSTED_PROXIES` | empty | IPs or networks (CIDR) of your proxies, comma-separated, for example `172.18.0.0/16` |

:::warning Behind a proxy, TRUSTED_PROXIES is required
If the application is behind a proxy (Nginx, a load balancer), every request reaches it from the proxy's IP. Without `TRUSTED_PROXIES`, all users share that IP and the limit of 10 sign-ins per minute is split among everyone. With it, the application reads the real IP from the `X-Forwarded-For` header, but only when a proxy on the list sets it.
:::

Limits are kept in Valkey. If Valkey doesn't respond, the application lets requests through without limits and logs it, so that nobody is locked out. While the outage lasts it tries again every 30 seconds, and limits come back on their own as soon as Valkey responds.

## Environment

| Variable | Required | What it is |
|---|---|---|
| `ENV` | Yes | `development` or `production`. In `development`, the API logs every SQL query |
