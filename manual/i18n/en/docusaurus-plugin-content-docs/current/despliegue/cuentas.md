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

:::note Without email, the password can't be changed from the application
Without SMTP, an account can't change or recover its password on its own (the application doesn't offer the link). If you want it to be able to, set up [email](correo.md).
:::

## Open sign-up

With `SIGNUP_ENABLED=true` (and deploying again), anyone can sign up from the sign-in page. Think it over first: each account uses disk and, if you have platform AI, can spend its free uses. The [per-account limits](variables.md) bound the damage but don't prevent it.

The `create_user` script keeps working with sign-up open.
