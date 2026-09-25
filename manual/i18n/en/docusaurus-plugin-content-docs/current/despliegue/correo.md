---
title: Configure email
sidebar_label: Email
---

The application sends email through an **SMTP** server of your choice: your email provider's or a sending service (Brevo, Amazon SES, Mailgun, Gmail with an app password…). It does not depend on any particular one.

## Which emails it sends

| Email | When |
|---|---|
| Confirm the email | When the account is created, and when the user clicks **Resend link** |
| Recover or change the password | The user asks for it from the sign-in screen or from Preferences |

They go out in the account language (or, if it is not set, in the one shown on screen), in Spanish or English.

- **The `worker` service sends them**, not the API: if `worker` is stopped, emails wait in the queue and go out when it starts. Its logs (`docker compose logs worker`) record every send and every failure, with the user id and without the address.
- **Email links use `WEBSITE_DOMAIN`.** If it keeps the development value (`http://localhost:5173`), emails arrive fine but their link leads nowhere. See [Variables](variables.md).
- **Without SMTP the application works the same:** it does not offer to recover or change the password, says so on screen, and does not ask to confirm the email.

## Variables

| Variable | Value | Notes |
|---|---|---|
| `SMTP_HOST` | Server, for example `smtp-relay.brevo.com` | **Without it nothing is sent**, and the application works anyway |
| `SMTP_PORT` | Port | Usually `587` with `starttls` or `465` with `tls` |
| `SMTP_SECURITY` | `starttls`, `tls` or `none` | See the table below |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Server credentials | Empty if the server does not require sign-in |
| `EMAIL_FROM` | Sender, for example `Applications Tracker <no-reply@yourdomain.com>` | **Required if `SMTP_HOST` is set**: without it, the API does not start |
| `SMTP_TIMEOUT_SECONDS` | Seconds to wait (30 by default) | Optional |

| `SMTP_SECURITY` | When |
|---|---|
| `starttls` (default) | Port 587: the connection starts unencrypted and is encrypted before anything is sent |
| `tls` | Port 465: encrypted from the start |
| `none` | Only for a test server on the same machine. **Never with a real server**: the password would travel unencrypted |

With `starttls` or `tls`, if the server offers no encryption, the application **does not send** the email in clear text: it treats it as failed.

## Check that it works

With the containers running:

```bash
docker compose exec api python -m app.scripts.send_test_email you@email.com
```

| What you see | What it means |
|---|---|
| `Aceptado por <server>:<port> (<encryption>) para you@email.com.` | The server accepted the email. Check your inbox, and the spam folder too |
| `SMTP sin configurar: define SMTP_HOST y EMAIL_FROM.` | The configuration is missing, or the container was not recreated after changing `.env` |
| `No se envió (es seguro reintentar): …` | The server did not accept it: wrong address or port, rejected credentials, no encryption available… The message says why |
| `Resultado desconocido, puede que haya salido: …` | The connection dropped while sending. Check the inbox before trying again |

The script's messages are in Spanish.

## Common problems

- **The server does not allow SMTP.** Many hosting providers block port 25 by default, and some also 465 and 587, on new accounts. If the test hangs until the timeout, ask the provider to unblock the port or use a sending service that accepts port 587 or 2525.
- **The sender is not authorised.** Many services only let you send from addresses or domains you have verified with them. If `EMAIL_FROM` doesn't match, they reject the email.
- **Emails land in spam.** Set up **SPF**, **DKIM** and **DMARC** for the domain of `EMAIL_FROM` following your sending service's instructions. Without them, many servers distrust the email even though everything works.
