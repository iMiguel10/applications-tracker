---
title: Your obligations as controller
sidebar_label: Obligations as controller
---

Whoever deploys an installation and gives accounts to other people is the **data controller** for their data (GDPR). The author of the software is not: they don't see your installation or its data. This page sums up what falls to you and what the application already does for you.

:::caution This is not legal advice
It is an indicative guide using the GDPR and Spanish law as a reference. If your installation has real users outside your circle, review it with someone who knows your case.
:::

## When it applies to you

- **Only for you** (or household use): the GDPR does not apply to purely personal activity (art. 2.2.c). You can skip this page.
- **You give accounts to other people**, even for free or to friends: you are responsible for their data and what follows applies to you.

## What data the application processes

| Data | Where | How long it is kept |
|---|---|---|
| Email and password (hashed) | SuperTokens database | Until the account is deleted |
| Applications, companies, history, interviews, reminders and notes | Application database | Until the person deletes them or deletes the account |
| Professional profile (with contact details) | Application database | Same |
| Uploaded and generated PDFs | `files_data` volume | Same |
| Preferences (language, time zone, notifications) | Application database | Until the account is deleted |
| AI proposals (the generated text, tokens and cost) and consents | Application database | Until the account is deleted (if the application is deleted, the proposal stays without it, as a usage record) |
| Own AI keys | Application database, **encrypted** | Until the person removes it or deletes the account |
| Record of notifications sent | Application database | 90 days after sending (some, while the application stays inactive) |
| IP and email of attempts (request limits) | Valkey | Minutes or hours, as long as each window lasts |
| IP, requested address and browser of each request | Container logs (`web`, `api`) | Whatever Docker or Coolify keeps: set up their rotation |
| Backups of all of the above | Server folder and, if you set it up, off the server | 7 daily and 4 weekly (about 5 weeks); outside, whatever you decide |

The browser also keeps the session cookie and, without cookies, the theme, the language and some interface preferences. There are no analytics or third-party cookies.

## Record of processing activities

The GDPR asks you to keep a record of what you do with the data (art. 30). With fewer than 250 employees it is only mandatory if the processing is not occasional, and an application in use is not: keep it. You can start from this table, with your controller details on top (name and contact) and the date:

| Processing | Purpose | Legal basis | Data | Retention |
|---|---|---|---|---|
| Accounts and use of the application | Providing the service | Contract (art. 6.1.b) | Email, password, job search data, profile, documents, preferences | Until the account is deleted, plus the backups |
| Email notifications | Reminders, interviews, digest and finished proposals | Contract: a feature of the service each person turns off in **Email notifications** | Email and what the notification says | Record of sends: 90 days |
| AI | Tailoring the CV and writing cover letters | Consent (art. 6.1.a): the application asks for it per provider before sending anything and stores it | Profile **without contact details** and the job description | Proposals: until the account is deleted |
| Security | Stopping abuse and attacks (request limits, logs) | Legitimate interest (art. 6.1.f) | IP, email of attempts, requests | Minutes in Valkey; logs according to their rotation |
| Backups | Recovering the data if something fails | Legitimate interest and security duty (art. 32) | All of the above | About 5 weeks on the server; outside, whatever you decide |

## Processors

Every external service that receives data on your behalf is a **processor** and you need a processing agreement with it (art. 28). Big providers include it in their terms (look for a *DPA* or *Data Processing Agreement*). It depends on what you turn on:

| Service | When | What it receives | What to check |
|---|---|---|---|
| Hosting (VPS, cloud) | If the server is not yours | Everything | Its DPA and which country the data is in |
| Email (SMTP) | With [email](correo.md) | Each person's email and the content of their notifications | Its DPA |
| Platform AI: Anthropic, OpenAI or Groq | With [platform AI](ia-de-la-plataforma.md) | The profile without contact details and the job description | Its DPA, that API data is not used for training, and the **transfer to the US** (EU-US Data Privacy Framework or standard contractual clauses) |
| Ollama | If it runs on someone else's server | The same | An Ollama on a machine of yours is not a processor: nothing leaves |
| Store for the off-server backups (S3, R2, someone else's NAS) | With `BACKUP_RCLONE_REMOTE` | Everything | Its DPA. [Encrypting them](copias-de-seguridad.md#encrypt-the-backups-stored-outside) greatly reduces the risk |

With **own keys**, the person uses their own account with the provider: the contract is theirs, not yours. Even so, the application sends their data there, and your privacy policy must say so.

## Informing your users

Each person must know who you are, what data you process, what for, who you share it with, how long you keep it and how to exercise their rights (arts. 13 and 14): that is the **privacy policy**. If you offer the service to other people, you also need a **legal notice** with your details (Spanish LSSI-CE, art. 10) and **terms**.

The application doesn't ship these pages yet: they will come as templates you fill in with variables ([issue #3](https://github.com/iMiguel10/applications-tracker/issues/3)). Meanwhile, if you have users, publish them yourself and send them the link. The tables above are the basis of their content.

In Spain, a minor's consent is only valid from **14 years old** (LOPDGDD, art. 7): don't give accounts to anyone younger.

## Handling rights requests

You have **one month** to answer each request, extendable by two more in complex cases (art. 12.3). First check that it comes from the account holder, for example from the account's email.

| Right | How |
|---|---|
| **Access and portability** (arts. 15 and 20) | The person downloads everything in **Preferences › Your data**. If they can't sign in, you generate it with [`export_user`](cuentas.md#export-an-accounts-data) |
| **Rectification** (art. 16) | They correct their data in the application. You change the email with [`change_email`](cuentas.md#change-an-accounts-email) |
| **Erasure** (art. 17) | **Delete account**, in Preferences: it deletes everything at once. It stays in the backups for about 5 weeks, until they expire; tell them if they ask |
| **Withdrawing consent and objection** (arts. 7.3 and 21) | Each notification is turned off in **Email notifications**, and the AI with **Revoke permission for…** in the **Artificial intelligence** card |
| **Restriction** (art. 18) | The application has no feature to block an account without deleting it: handle it case by case |

If you don't handle a request, the person can complain to the supervisory authority (in Spain, the [AEPD](https://www.aepd.es)).

## Security

The application ships with HTTPS, hashed passwords, request limits, expiring sessions, encrypted AI keys and daily [backups](copias-de-seguridad.md). What falls to you (art. 32):

- Keep the server and the application [up to date](actualizar.md).
- Keep the secrets **off the server**, in a password manager.
- **Encrypt the backups that leave the server** and, if anyone else can physically reach the machine, the disk.
- Set up the **rotation of the Docker or Coolify logs**: they contain IPs.
- Check now and then that the backups can be restored.

## If there is a security breach

A breach is any access, loss or leak of personal data: a compromised server, an exposed backup, a lost laptop with a `.env`.

1. **Contain it.** Change the compromised secrets in the [variables](variables.md) and redeploy. For AI keys, add a new key to `AI_KEYS_ENCRYPTION_KEYS` and run `python -m app.scripts.rotate_ai_keys` in `api`. If data was altered, [restore](copias-de-seguridad.md#restore) an earlier backup.
2. **Notify the supervisory authority within 72 hours** of becoming aware of it (art. 33), unless it is unlikely to result in a risk to people. In Spain, on the AEPD's online office.
3. **Tell the affected people** without delay if the risk is high (art. 34): what happened and what they should do (for example, change their password and that of other sites where they use the same one).
4. **Record it**: what happened, its effects and what you did, even if you don't notify it (art. 33.5).

## The AI

- **It is not a high-risk system** under the EU AI Act, in our reading: the high-risk ones in employment are those used by whoever hires to select or evaluate candidates. Here it is the candidate who uses it, on their own data, and decides what to send.
- **Transparency:** the person requests each proposal, sees which model generated it and reviews every change before creating the PDF. Nothing goes out without their approval.
- **Minimisation:** the AI never receives the profile's contact details (name, email, phone, location or links), and only with prior consent for each provider.
