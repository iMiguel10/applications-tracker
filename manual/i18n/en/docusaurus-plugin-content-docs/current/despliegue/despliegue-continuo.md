---
title: Continuous deployment
sidebar_label: Continuous deployment
---

With continuous deployment, every new version that passes the tests deploys itself on Coolify, without opening the panel. It is optional and only works with [Coolify](coolify.md) and a GitHub repository (the CI is GitHub Actions).

## How it works

A push to `main` runs the CI (style, tests, build, documentation and production images). If everything passes, the last step, the `deploy` job, does this:

1. **Checks that `main` is still that commit.** Coolify always deploys the latest of the branch, not a specific commit; if `main` has already moved on, deploying would ship a commit this CI hasn't tested. In that case it ends without deploying and without failing: the new commit's CI deploys it.
2. **Requests the deployment** from Coolify's API and waits, polling its status every 10 seconds, for up to 30 minutes (a build usually takes about 7).
3. **Checks the result:** that Coolify deployed that commit and that your domain's `/api/v1/health` answers `ok`.

The job fails if the deployment ends in `failed` or `cancelled`, if it doesn't finish within 30 minutes, if Coolify rejects the token, or if it deployed another commit or the application doesn't respond. The reason is in the job's log.

## Set it up

1. **Create a token in Coolify** (*Keys & Tokens › API tokens*, or the equivalent name in your version) with the `read` and `deploy` permissions, **and no others**. With only `deploy` the deployment is launched but can't be followed, and the job fails. Dedicate it to this: don't use it for anything else.
2. **Turn off *Auto Deploy*** on the Coolify resource. Otherwise Coolify also deploys on every push without waiting for the CI, even if it fails.
3. **Note the resource's identifier**: the application UUID that appears in the URL of its page in Coolify.
4. **In GitHub** (*Settings › Secrets and variables › Actions*):

    | Where | Name | Value |
    |---|---|---|
    | Secret | `COOLIFY_URL` | The address of your Coolify panel |
    | Secret | `COOLIFY_TOKEN` | The token from step 1 |
    | Secret | `COOLIFY_APP_UUID` | The UUID from step 3 |
    | Variable | `PRODUCTION_URL` | The application's public address (`APP_URL`) |

    The `PRODUCTION_URL` variable acts as a switch: **without it the job doesn't run** (on a fork or another installation, nobody deploys by mistake). To pause continuous deployment, delete it.

5. **Coolify's panel must be reachable from GitHub** (a normal GitHub runner calls its API): with the panel only on your local network, the job can't reach it. It needs to be public (preferably with two-factor authentication) or use a runner of your own, which this guide doesn't cover.

**What you should see:** the next push to `main` that passes the CI shows a green *Producción · despliegue* job, and its log ends with `Desplegado <commit>` and `https://tracker.example.com responde`. GitHub also records it as a deployment in the `production` environment.

## If it fails

The job's messages are in Spanish.

| Job message | What to do |
|---|---|
| `Coolify rechazó el token (401/403)… necesita los permisos read y deploy` | Check the token: `read` and `deploy` permissions, and that it is the one in `COOLIFY_TOKEN`. Repeating won't fix it |
| `Coolify respondió 404` | Wrong `COOLIFY_APP_UUID` or `COOLIFY_URL` |
| `El despliegue terminó en 'failed'` | The build or start failed. The full log is in Coolify's panel, in the resource's deployments. Usually: a required variable is missing |
| `Coolify desplegó X y no Y` | `main` moved on in the meantime. Wait for the new commit's CI |
| `…/api/v1/health no responde tras el despliegue` | It deployed but the application doesn't answer: look at the `api` logs in Coolify |

To deploy by hand at any time, **Deploy** in Coolify's panel still works.
