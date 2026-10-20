---
title: Creating accounts
sidebar_label: Accounts
---

In production **sign-up comes closed** (`SIGNUP_ENABLED=false`): the sign-in page doesn't offer creating an account and the sign-up page explains it is closed. You create the accounts with a script. Existing ones work as before.

## Create an account

In the `api` service:

- **Coolify:** in the resource, open the `api` service's terminal. If the panel's terminal doesn't work, over SSH: `docker exec -it $(docker ps --format '{{.Names}}' | grep '^api-') <command>`.
- **Without Coolify:** `docker compose -f compose.prod.yml exec api <command>`.

```bash
python -m app.scripts.create_user ana@example.com
python -m app.scripts.create_user ana@example.com --language en   # account and email in English
```

The account is created with the email already verified and a random password nobody knows. The person chooses theirs with a link:

| Installation | What happens |
|---|---|
| **With [email](correo.md)** | They get an email ("Your Applications Tracker account is ready") with the link |
| **Without email**, or if sending fails | The script **prints the link** for you to pass on |

The link expires in **60 minutes**. If it expires, they can ask for another one with **Forgot your password?**, as long as the installation sends email. Without email, delete the account and create it again.

**What you should see:** the script finishes without an error and, opening the link in the browser, the page to choose the password appears. The script does nothing if an account with that email already exists.

:::note Without email, a forgotten password can't be recovered
Without SMTP, each person can **change** their password in **Preferences** by typing the current one, but can't **recover** it if they forget it: there's no link to send. In that case, delete their account and create it again with the script, or set up [email](correo.md).
:::

## Open sign-up

With `SIGNUP_ENABLED=true` (and deploying again), anyone can sign up from the sign-in page. Think it over first: each account uses disk and, if you have platform AI, can spend its free uses. The [per-account limits](variables.md) bound the damage but don't prevent it.

The `create_user` script keeps working with sign-up open.

## Demo account

To let other people try the application without handing them an account, you can keep a public account (`demo@example.com`) with a password everyone knows. Since anyone can make a mess of it, it is **recreated from scratch every day**.

1. Add the `DEMO_PASSWORD` variable (the password you want to publish) and redeploy.
2. Create the account the first time, in the `api` service's terminal:

    ```bash
    python -m app.scripts.reset_demo
    ```

3. Schedule the same command daily. In Coolify: in the resource, **Scheduled Tasks** → add a task with the command `python -m app.scripts.reset_demo`, the `api` container and the frequency `0 4 * * *`. Without Coolify, a `cron` entry on the server: `0 4 * * * docker compose -f compose.prod.yml exec -T api python -m app.scripts.reset_demo`.

Each run **deletes the whole account** (applications, documents, profile, AI keys, open sessions) and creates it again with a verified email, that password and these limits: 15 applications, 10 companies, 10 reminders, 3 documents, 2 MB of storage and **no** AI proposals. Email notifications are off. Anyone signed in at that moment is signed out. With `--email` and `--language` you can change the address and the language.

**What you should see:** the script prints `Cuenta de demostración … lista`, you can sign in with `demo@example.com` and the password, and **Preferences** shows the account usage with those limits.

:::caution The password is public
Don't put real data in that account. If someone changes its password, it stays that way until the next reset. Coolify's server clock may be in UTC: adjust the cron if the local time matters.
:::
