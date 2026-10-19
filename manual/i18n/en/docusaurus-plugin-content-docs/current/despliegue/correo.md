---
title: Configure email
sidebar_label: Email
---

The application sends email through an **SMTP** server of your choice: your email provider's or a sending service (Brevo, Amazon SES, Mailgun, Gmail with an app password…). It does not depend on any particular one.

**Email is optional and is enabled after deploying, with variables only.** A freshly deployed installation sends nothing; to enable it, add the variables below and **deploy again** (in Coolify, **Deploy**; without it, `docker compose -f compose.prod.yml up -d --build`). Nothing else needs to change.

## Which emails it sends

| Email | When |
|---|---|
| Confirm the email | When the account is created, and when the user clicks **Resend link** |
| Recover or change the password | The user asks for it from the sign-in page or from Preferences |
| Account created by the administrator | When you create an account with [the accounts script](cuentas.md): it carries the link to choose the password |
| Notifications (reminder due, upcoming interview, weekly digest, applications without activity, AI proposal finished) | According to each user's preferences, only to verified emails. The `worker` decides them with scheduled tasks |

They go out in the account's language (or, if it hasn't set one, the one it sees on screen), in Spanish or English.

- **The `worker` service sends them**, not the API: if the `worker` is stopped, emails stay queued and go out when it starts. Its logs record each send and each failure, with the user's id and without the address (in Coolify, the `worker` service's logs; without it, `docker compose -f compose.prod.yml logs worker`).
- **Links in emails use `APP_URL`.** Check it if a link leads nowhere. See [Variables](variables.md).
- **The `worker` schedules the notifications.** Every minute, every 5 minutes or every hour, depending on the notification, it checks what is due. If the `worker` was stopped, notifications that came due more than 24 hours ago are not sent when it comes back (so as not to flood the inbox) and the weekly digest of a Monday on which it was stopped all day is lost. A notification never goes out twice for the same reason, and if a send fails without knowing whether the server accepted it, it is not repeated.
- **Without SMTP the application works anyway:** it doesn't offer password recovery or change, says so on screen, and doesn't ask to confirm the email. No notification is scheduled either: the **Email notifications** card in Preferences looks disabled and says the installation doesn't send emails.

## Variables

| Variable | Value | Notes |
|---|---|---|
| `SMTP_HOST` | Server, for example `smtp-relay.brevo.com` | **Without it nothing is sent**, and the application works anyway |
| `SMTP_PORT` | Port | Usually `587` with `starttls` or `465` with `tls` |
| `SMTP_SECURITY` | `starttls`, `tls` or `none` | See the table below |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Server credentials | Empty if the server doesn't ask for sign-in |
| `EMAIL_FROM` | Sender, for example `Applications Tracker <no-reply@yourdomain.com>` | **Required if there is `SMTP_HOST`**: without it, the API doesn't start |

| `SMTP_SECURITY` | When |
|---|---|
| `starttls` (default) | Port 587: the connection starts unencrypted and is encrypted before anything is sent |
| `tls` | Port 465: encrypted from the start |
| `none` | Only for a test server on the same machine. **Never with a real server**: the password would travel unencrypted |

With `starttls` or `tls`, if the server doesn't offer encryption, the application **doesn't send** the email in the clear: it treats it as failed.

## Check that it works

With the installation already redeployed, in the `api` service's terminal (or with `docker exec -it <api-container> …`; without Coolify, `docker compose -f compose.prod.yml exec api …`):

```bash
python -m app.scripts.send_test_email you@email.com
```

| What you see | What it means |
|---|---|
| `Aceptado por <server>:<port> (<encryption>) para you@email.com.` | The server accepted the email. Check your inbox, and the spam folder too |
| `SMTP sin configurar: define SMTP_HOST y EMAIL_FROM.` | The configuration is missing, or you haven't deployed again after adding it |
| `No se envió (es seguro reintentar): …` | The server didn't accept it: wrong address or port, rejected credentials, encryption unavailable… The message says why |
| `Resultado desconocido, puede que haya salido: …` | The connection dropped while sending. Check the inbox before trying again |

The script's messages are in Spanish.

## Common problems

- **The server doesn't allow sending SMTP.** Many server providers block port 25 by default, and some also 465 and 587, on new accounts. If the test hangs until the timeout, ask the provider to unblock the port or use a sending service that supports 587 or 2525.
- **The sender isn't authorized.** Many services only let you send from addresses or domains you have verified with them. If `EMAIL_FROM` doesn't match, they reject the email.
- **Emails land in spam.** Set up **SPF**, **DKIM** and **DMARC** for the domain in `EMAIL_FROM` following your sending service's instructions. Without them, many servers distrust you even if everything works.
- **Gmail's or Outlook's unsubscribe button doesn't appear on notifications.** Each notification carries the one-click unsubscribe headers (`List-Unsubscribe`), but Gmail and Yahoo only show the button if the email is signed with **DKIM**. The unsubscribe link in the email footer works anyway.
