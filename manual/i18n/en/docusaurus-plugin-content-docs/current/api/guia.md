---
title: Integration guide
sidebar_label: Integration guide
---

The Applications Tracker API is a REST API with JSON. Everything the web application does can be done through it, with the same rules: the web application is just another client.

- **Route base:** `https://<your API>/api/v1`. Authentication routes live under `https://<your API>/auth`.
- **Full reference:** every endpoint, with its parameters, bodies and responses, is in the **Reference** section of this menu, generated from the same OpenAPI contract the API publishes.
- **To try things out:** the API itself serves Swagger at `/docs`, where you can run real requests.

:::note Language of the reference
The generated reference is in Spanish, because it comes straight from the descriptions in the API code. Keeping a second, English contract in sync would defeat its purpose: being generated, never written by hand.
:::

## Authentication

The API uses **SuperTokens** sessions. An integration works with two tokens it receives in the response **headers** when signing in:

| Token | What for | Lasts |
|---|---|---|
| Access token (`st-access-token`) | Sent with every request: `Authorization: Bearer <token>` | 5 minutes |
| Refresh token (`st-refresh-token`) | Requests a new pair of tokens when the access token expires | Until the session is closed |

```bash
# 1. Sign in: the tokens come in the response headers
curl -si -X POST https://<your API>/auth/signin \
  -H 'Content-Type: application/json' -H 'st-auth-mode: header' \
  -d '{"formFields":[{"id":"email","value":"ana@example.com"},{"id":"password","value":"her-password"}]}'
#    → st-access-token: eyJ...   st-refresh-token: tOb...

# 2. Call the API with the access token
curl -s https://<your API>/api/v1/me -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. When a call returns 401, refresh with the refresh token
curl -si -X POST https://<your API>/auth/session/refresh \
  -H 'st-auth-mode: header' -H "Authorization: Bearer $REFRESH_TOKEN"
#    → a new access token AND a new refresh token

# 4. Sign out
curl -s -X POST https://<your API>/auth/signout -H "Authorization: Bearer $ACCESS_TOKEN"
```

:::warning A refresh token works only once
Every refresh returns **a new refresh token as well** and invalidates the previous one. If you reuse one that was already used, SuperTokens treats it as **session theft** and closes the session. After every refresh, store both new tokens, and let only one process refresh at a time.
:::

Responses from `/auth/signup` and `/auth/signin` are **always 200**. The result is in the `status` field: `OK`, `WRONG_CREDENTIALS_ERROR` or `FIELD_ERROR` (for example, a password that does not meet the policy, with details in `formFields`). Check `status`, not the HTTP code.

Signing out revokes the refresh token immediately. An access token already issued stays valid until it expires, 5 minutes at most.

### Recover a password

Two calls, without a session:

1. `POST /auth/user/password/reset/token` with `{"formFields":[{"id":"email","value":"…"}]}`. It sends an email with a link to `<the web application>/reset-password?token=…&tenantId=…`. It answers **`OK` whether or not the account exists**, so it cannot be used to find out whether an email is registered.
2. `POST /auth/user/password/reset` with `{"method":"token","token":"<token from the link>","formFields":[{"id":"password","value":"…"}]}`. The token works **only once** and expires after an hour: if it is not valid, `status` is `RESET_PASSWORD_INVALID_TOKEN_ERROR`.

Changing the password **revokes every session of the user**: any refresh tokens an integration held stop working and it has to sign in again.

### Verify the email

On sign-up (`POST /auth/signup`), the API sends by itself an email with a link to `<the web application>/verify-email?token=…&tenantId=…`.

- `POST /auth/user/email/verify` with `{"method":"token","token":"<token from the link>"}` verifies it, without needing a session. The token expires after 24 hours and works once: if it is not valid, `status` is `EMAIL_VERIFICATION_INVALID_TOKEN_ERROR`.
- `GET /auth/user/email/verify` (with a session) says whether it is verified: `{"status":"OK","isVerified":…}`.
- `POST /auth/user/email/verify/token` (with a session) sends the link again, or answers `EMAIL_ALREADY_VERIFIED_ERROR` if it already is.

The API works without verifying the email. Routes that require it will answer **403** with `code: email_not_verified`; today none requires it yet.

### Installation capabilities

`GET /api/v1/meta` is public and says what this installation offers. Today it only includes `email_enabled`: with `false` there is no email server, and requesting a recovery answers the same but sends nothing.

## Errors

Application errors always have this shape:

```json
{ "detail": "Application not found", "code": "not_found" }
```

`detail` is text for people and may change. **`code` is stable**: use it to decide what to do.

| HTTP | When | Example `code` values |
|---|---|---|
| 401 | No session, or the access token expired | — (refresh and retry) |
| 404 | It does not exist, **or it belongs to another user** | `not_found` |
| 409 | The request is valid, but a rule prevents it | `invalid_transition`, `company_in_use`, `company_name_taken`, `applications_limit_reached`, `companies_limit_reached`, `reminders_limit_reached`, `reminder_not_pending`, `cannot_undo_initial_change` |
| 422 | Data that breaks a business rule | `changed_at_in_future`, `changed_at_before_last_change`, `applied_at_required`, `salary_range_invalid` |

A resource belonging to another user returns **404, exactly like a missing one**: the API never confirms an id exists unless it is yours.

**Format** errors (a missing required field, a wrong type) are also 422, but with FastAPI's standard shape: `detail` is a list with the location and reason of each failure, with no `code`.

## Lists

Lists are paginated with `page` (from 1) and `limit` (20 by default, 100 at most), and always answer with the same shape:

```json
{ "items": [ ... ], "total": 57, "page": 1, "limit": 20, "pages": 3 }
```

They are sorted with `sort_by` and `order` (`asc` or `desc`). The sortable fields and the filters of each list are on its reference page.

## Dates

- Instants (`due_at`, `scheduled_at`, `changed_at`, `created_at`…) are **ISO 8601 with a time zone**, for example `2026-10-01T09:30:00Z`. One without a time zone is rejected with 422.
- `applied_at` is a **day**, with no time: `2026-10-01`.

## Statuses and transitions

An application's status **is not changed with `PATCH`**: it has its own endpoint (`POST /applications/{application_id}/status-changes`), which records the change in the history. Every application comes with `allowed_transitions`, the statuses it can move to from the current one; any other is rejected with `invalid_transition`.

## Limits

| Resource | Limit per account | When exceeded |
|---|---|---|
| Applications | 5,000 | 409 `applications_limit_reached` |
| Companies | 2,000 | 409 `companies_limit_reached` |
| Pending reminders | 500 | 409 `reminders_limit_reached` |
| Notes | 5,000 characters | 422 |

## Calls from a browser

For security, the API only accepts browser requests from the origins configured in the installation (`CORS_ORIGINS`), which are usually just the web application's own. A server-to-server integration is not affected.
