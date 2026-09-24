---
title: Backup and restore
sidebar_label: Backups
---

A full backup has **three** pieces:

1. The application database (`db`).
2. The SuperTokens database (`supertokens-db`): accounts and passwords.
3. The files in the `files_data` volume.

Valkey needs no backup: it holds the queue of waiting tasks, not data.

:::warning Order matters
Back up **the databases first and the files after**. That way, a file uploaded between both steps at worst ends up in the backup with nothing using it: it is surplus, but breaks nothing. In the opposite order, you could restore a database pointing to a file that is not in the backup.
:::

## Making the backup

From the project folder, with the containers running:

```bash
mkdir -p backup

# 1. Application database
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backup/app.dump

# 2. SuperTokens database
docker compose exec -T supertokens-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backup/supertokens.dump

# 3. Files, always after the databases
docker compose exec -T api tar -czf - -C /data/files . > backup/files.tar.gz
```

To check the backup is valid, list its contents. It must show the tables, with no errors:

```bash
docker compose exec -T db pg_restore --list < backup/app.dump | head
```

Keep the backups **off the server**. A backup on the same disk does not protect you if the disk fails.

## Restoring

:::danger
Restoring **replaces** the current data with the backup's.
:::

1. Stop the API and the worker, so nothing writes while you restore:

    ```bash
    docker compose stop api worker
    ```

2. Restore both databases:

    ```bash
    docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < backup/app.dump
    docker compose exec -T supertokens-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < backup/supertokens.dump
    ```

3. Restore the files:

    ```bash
    docker compose run --rm --no-deps -T --entrypoint sh api -c 'rm -rf /data/files/* && tar -xzf - -C /data/files' < backup/files.tar.gz
    ```

4. Start everything again:

    ```bash
    docker compose up -d
    ```

If the backup came from an older version of the application, the API applies any missing migrations on start-up.
