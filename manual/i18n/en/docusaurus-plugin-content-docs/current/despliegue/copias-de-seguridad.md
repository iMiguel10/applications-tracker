---
title: Backup and restore
sidebar_label: Backups
---

The `backup` service in `compose.prod.yml` makes the backups by itself: **there is nothing to schedule**. This page explains what it backs up, how to check it works, how to take backups off the server and how to restore them.

## What it backs up

A complete backup is **three** pieces, in this order:

1. The application database (`db`): `app.dump`.
2. The SuperTokens database (`supertokens-db`): `supertokens.dump`, with the accounts and passwords.
3. The files in the `files_data` volume: `files.tar.gz`.

Plus a `SHA256SUMS` to check on restore that nothing got corrupted. Valkey is not backed up: it holds the queue of waiting tasks, not data.

The order matters: files go **after** the databases, so every document in the backup has its file (at most one is left over, and the `worker` deletes every day the files no document uses). And SuperTokens goes after the application so that an account created between the two dumps doesn't leave an application row without an account.

## When and where

- **When:** every night at 3:00, in the time zone of `TZ` (`Europe/Madrid` by default). Change it with `BACKUP_SCHEDULE`, in cron format (`0 3 * * *`). The server clock may be in UTC: don't be surprised if the time in the server's logs is different.
- **Where:** in a folder **on the server**, `BACKUP_HOST_DIR` (`/var/backups/applications-tracker` by default), with one subfolder per backup: `2026-10-19_030000/`. It is a folder, not a Docker volume, so you can see it and take it to a NAS or a disk.
- **How many:** the `BACKUP_KEEP_DAILY` most recent (7) and, in addition, the last one of each of the previous `BACKUP_KEEP_WEEKLY` weeks (4). The rest are deleted. A week that already has daily backups doesn't use up a weekly slot.

## Check that they are made

The first backup is tonight's; to avoid waiting, make one now (you can also do this at any time):

```bash
docker exec <backup-container> backup                            # Coolify, over SSH
docker compose -f compose.prod.yml exec backup backup            # without Coolify
```

(In Coolify the `backup` service's terminal also works, running `backup`.) **What you should see:** lines ending in `copia 2026-10-19_153012 terminada`, and on the server:

```bash
ls /var/backups/applications-tracker
# 2026-10-19_153012
ls /var/backups/applications-tracker/2026-10-19_153012
# app.dump  files.tar.gz  SHA256SUMS  supertokens.dump
```

**If a backup fails, you can see it:** the `backup` service goes *unhealthy* if the last backup failed or if the last successful one is more than `BACKUP_MAX_AGE_HOURS` hours old (26). Coolify shows it on the resource. The reason is in the `backup` service's logs. After a new deployment the counter starts from zero: it doesn't go unhealthy because of an old backup. The script's log lines are in Spanish.

## Off the server

A backup on the same disk doesn't protect you if the disk fails. With `BACKUP_RCLONE_REMOTE`, each new backup is sent elsewhere with [rclone](https://rclone.org), which talks to S3 and compatibles, SFTP, SMB and many more. The value is an rclone connection string with the destination:

```text
# S3 or compatible (here, Cloudflare R2)
BACKUP_RCLONE_REMOTE=:s3,provider=Cloudflare,access_key_id=<id>,secret_access_key=<secret>,endpoint=https://<account>.r2.cloudflarestorage.com:bucket/applications-tracker

# SFTP (a NAS or another server)
BACKUP_RCLONE_REMOTE=:sftp,host=nas.local,user=backup,pass=<obscured password>:/volume1/backups/applications-tracker
```

SFTP or SMB passwords go **obscured** with `rclone obscure <password>` (it doesn't encrypt: it only keeps it from being read at a glance). Empty, nothing is sent.

- **Nothing is ever deleted there.** The application only copies (`rclone copy`, not `sync`): if someone deletes the backups on the server, the ones outside remain. That is why you set the retention there, with the store's own rules (for example, a bucket's lifecycle).
- If sending fails, the backup fails (even though the local one is there) and the service goes *unhealthy*.
- The store's keys go in an environment variable: treat it as a secret.

### Encrypt the backups stored outside

The backups hold **all your users' data** in the clear. If they leave the server for a store you don't fully control (an S3 bucket, a shared NAS), **encrypt them**: as the [controller](obligaciones.md), it is what is expected of you, and if someone gets into that store they won't be able to read them. rclone encrypts with a `crypt` destination that wraps the usual one: it encrypts the content and the file names before sending them.

1. **Generate two long random passwords** (the second is the *salt*) and keep them in your password manager: **without them, the backups stored outside can't be recovered**.
2. **Obscure them** for the variable, with the `backup` service image (it ships rclone):

    ```bash
    docker exec <backup-container> rclone obscure '<password>'
    docker exec <backup-container> rclone obscure '<salt>'
    ```

3. **Wrap the destination** in `BACKUP_RCLONE_REMOTE`: the previous one goes in single quotes in `remote`, and `password` and `password2` take the two obscured values:

    ```text
    # S3 or compatible, encrypted
    BACKUP_RCLONE_REMOTE=:crypt,remote=':s3,provider=Cloudflare,access_key_id=<id>,secret_access_key=<secret>,endpoint=https://<account>.r2.cloudflarestorage.com:bucket/applications-tracker',password=<obscured password>,password2=<obscured salt>:

    # SFTP, encrypted
    BACKUP_RCLONE_REMOTE=:crypt,remote=':sftp,host=nas.local,user=backup,pass=<obscured password>:/volume1/backups/applications-tracker',password=<obscured password>,password2=<obscured salt>:
    ```

4. **Redeploy** and run a backup (`docker exec <backup-container> backup`).

**What you should see:** in the store, each backup's folder and its files have unreadable names (`le237ndr70jg…`) and their content can't be opened; the local copy on the server stays in the clear. How to bring it back is in [Restore](#restore).

`rclone obscure` doesn't encrypt (anyone with rclone can undo it): what protects the backups is that the variable, and the passwords, only live on the server and in your password manager.

#### Make sure you can recover them without the server

The backups stored outside are for when you lose the server, and the variable goes with it: Coolify keeps it in its own database, on that same server. If the passwords only lived there, **the encrypted backups can't be recovered**; rclone has no back door.

- **Keep in your password manager** the two passwords in the clear and the whole value of `BACKUP_RCLONE_REMOTE` (it also holds the store's keys). If you only have the obscured ones, `docker exec <backup-container> rclone reveal '<obscured value>'` returns each one in the clear while you still have the server.
- **Test it once from another machine**, with rclone and only what is in the password manager: `rclone copy "<BACKUP_RCLONE_REMOTE value>/<backup>" ./test` and, inside the folder, `sha256sum -c SHA256SUMS`. If everything says `OK`, you don't depend on the server to recover them.

#### The backups on the server are in the clear

Only what leaves with `BACKUP_RCLONE_REMOTE` is encrypted. The backups in `/var/backups/applications-tracker` are **in the clear on purpose**: they are on the same disk as the live databases, which aren't encrypted either, so whoever can read that folder can already read the data; and encrypting them would make restoring, which is what they are for, slower and more delicate.

- **If the server is somewhere others can physically reach** (at home, in an office), what protects the data and the backups at once is **encrypting the whole disk** (LUKS on Linux), usually when installing the system.
- **Don't move the backups by hand as they are** to a NAS or an external disk: they would leave in the clear. Set that destination as `BACKUP_RCLONE_REMOTE` with `crypt` and every new backup leaves encrypted on its own.

## Secrets to keep elsewhere

Backups deliberately **don't include** these values. Keep them in a password manager, **outside the server and the backups**:

| Secret | If you lose it |
|---|---|
| `AI_KEYS_ENCRYPTION_KEYS` | The AI keys users stored are unreadable: they will have to enter them again |
| `APP_SECRET` | The unsubscribe links in emails already sent stop working |
| `POSTGRES_PASSWORD`, `SUPERTOKENS_DB_PASSWORD`, `SUPERTOKENS_API_KEY` | You can't rebuild the installation with the same databases |
| `BACKUP_RCLONE_REMOTE` (its keys) | You can't recover the backups stored outside |
| The two encryption (`crypt`) passwords, in the clear | The encrypted backups stored outside **can't be decrypted**: by nobody, you included |

## Restore

:::danger
Restoring **replaces** the two databases and the files currently in place with those of the backup.
:::

Restoring requires that **nobody is writing**: `api`, `worker` and `supertokens` must be stopped. If any connection to the databases remains, `restore` refuses to start and touches nothing. It doesn't touch anything either if the backup is damaged (the `SHA256SUMS` don't match).

1. **Choose the backup.** Look at the ones in the server folder (`ls /var/backups/applications-tracker`). A backup brought from outside (NAS, S3) is first placed in that folder, with its dated folder. If it is outside (encrypted too), bring it back with the `backup` service itself, which decrypts it with `BACKUP_RCLONE_REMOTE`:

    ```bash
    docker exec <backup-container> sh -c 'rclone copy "$BACKUP_RCLONE_REMOTE/2026-10-19_030000" /backups/2026-10-19_030000'
    ```

    `restore` then checks the `SHA256SUMS`: if decrypting or downloading had gone wrong, it touches nothing.

2. **Stop `api`, `worker` and `supertokens`.** With Coolify, over SSH (container names, with `docker ps`):

    ```bash
    docker stop <worker-container> <api-container> <supertokens-container>
    ```

    Without Coolify:

    ```bash
    docker compose -f compose.prod.yml stop worker api supertokens
    ```

3. **Restore.**

    ```bash
    docker exec <backup-container> restore 2026-10-19_030000 --yes            # Coolify
    docker compose -f compose.prod.yml run --rm backup restore 2026-10-19_030000 --yes   # without Coolify
    ```

    **What you should see:** the `SHA256SUMS` check, the restore of each database and of the files, and a last line `copia … restaurada: arranca de nuevo el stack`. Without `--yes`, it refuses and reminds you what it would replace.

4. **Start again**, in this order:

    ```bash
    docker start <supertokens-container> <api-container> <worker-container>
    ```

    (without Coolify, `docker compose -f compose.prod.yml up -d`). If the backup was from an earlier version of the application, `api` applies the missing migrations on start.

5. **Check** that `https://tracker.example.com/api/v1/health` answers `ok` and that you can sign in.

The passwords and keys must be the same ones the backup was made with (the ones [above](#secrets-to-keep-elsewhere)): if you restore into a new installation, set them before deploying.
