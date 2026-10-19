---
title: Upgrading to a new version
sidebar_label: Upgrading
---

Upgrading is **deploying again** the new version of the repository. There is nothing to run by hand.

- **With Coolify:** **Deploy**, or automatically with [continuous deployment](despliegue-continuo.md).
- **Without Coolify:** `git pull` and `docker compose -f compose.prod.yml up -d --build`.

## What happens

- **Migrations are automatic.** On start, `api` applies the pending database migrations before accepting requests. The `worker` waits for `api` to be healthy, so it never runs against an old schema.
- **Data is kept.** The databases, Valkey and the files live in volumes that a deployment doesn't touch.
- **There may be a few seconds without service** while `api` is recreated and migrates: if the web gives you a 502 error, the API isn't ready yet; wait and reload.
- **If you change `APP_URL`** (another domain), the `web` image is rebuilt, because the frontend carries the address inside. Changing domain also invalidates open sessions, because the cookies belong to the previous domain.
- **If you change a variable**, the affected service is recreated on deploy. A restart doesn't apply it.

## Before upgrading

**Make a backup.** A migration doesn't undo itself. If the `backup` service already made tonight's, that is enough; if not, make another one now (see [Backups](copias-de-seguridad.md)) and check it finished.

## If something goes wrong

If the new version doesn't start, `api` stays *unhealthy* and the deployment fails; the log says why (usually a new required variable that isn't set). Add it and deploy again. If a migration left the data in a bad state, [restore](copias-de-seguridad.md) the earlier backup.
