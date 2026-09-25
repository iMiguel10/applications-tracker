---
title: Guía de integración
sidebar_label: Guía de integración
---

La API de Applications Tracker es una API REST con JSON. Todo lo que hace la aplicación web se puede hacer a través de ella, con las mismas reglas: la aplicación web es un cliente más.

- **Base de las rutas:** `https://<tu API>/api/v1`. Las de autenticación van en `https://<tu API>/auth`.
- **Referencia completa:** cada endpoint, con sus parámetros, cuerpos y respuestas, está en la **Referencia** de este menú, generada del mismo contrato OpenAPI que publica la API.
- **Para probar:** la propia API sirve Swagger en `/docs`, donde se pueden ejecutar peticiones reales.

## Autenticación

La API usa sesiones de **SuperTokens**. Una integración trabaja con dos tokens que recibe en las **cabeceras** de la respuesta de inicio de sesión:

| Token | Para qué | Dura |
|---|---|---|
| Access token (`st-access-token`) | Se envía en cada petición: `Authorization: Bearer <token>` | 5 minutos |
| Refresh token (`st-refresh-token`) | Pide un par de tokens nuevo cuando caduca el access token | Hasta que se cierra la sesión |

```bash
# 1. Iniciar sesión: los tokens llegan en las cabeceras de la respuesta
curl -si -X POST https://<tu API>/auth/signin \
  -H 'Content-Type: application/json' -H 'st-auth-mode: header' \
  -d '{"formFields":[{"id":"email","value":"ana@example.com"},{"id":"password","value":"su-contraseña"}]}'
#    → st-access-token: eyJ...   st-refresh-token: tOb...

# 2. Llamar a la API con el access token
curl -s https://<tu API>/api/v1/me -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Cuando una llamada responda 401, renovar con el refresh token
curl -si -X POST https://<tu API>/auth/session/refresh \
  -H 'st-auth-mode: header' -H "Authorization: Bearer $REFRESH_TOKEN"
#    → un access token Y un refresh token nuevos

# 4. Cerrar sesión
curl -s -X POST https://<tu API>/auth/signout -H "Authorization: Bearer $ACCESS_TOKEN"
```

:::warning El refresh token solo sirve una vez
Cada renovación devuelve **también un refresh token nuevo** e invalida el anterior. Si reutilizas uno ya usado, SuperTokens lo trata como un **robo de sesión** y la cierra. Tras cada renovación, guarda los dos tokens nuevos, y que renueve un solo proceso a la vez.
:::

Las respuestas de `/auth/signup` y `/auth/signin` son **siempre 200**. El resultado va en el campo `status`: `OK`, `WRONG_CREDENTIALS_ERROR` o `FIELD_ERROR` (por ejemplo, una contraseña que no cumple la política, con el detalle en `formFields`). Comprueba `status`, no el código HTTP.

Cerrar sesión revoca el refresh token al momento. Un access token ya emitido sigue siendo válido hasta que caduca, como mucho 5 minutos.

### Recuperar la contraseña

Son dos llamadas, sin sesión:

1. `POST /auth/user/password/reset/token` con `{"formFields":[{"id":"email","value":"…"}]}`. Envía un email con un enlace a `<la aplicación web>/reset-password?token=…&tenantId=…`. Responde **`OK` exista o no la cuenta**, así que no sirve para saber si un email está registrado.
2. `POST /auth/user/password/reset` con `{"method":"token","token":"<token del enlace>","formFields":[{"id":"password","value":"…"}]}`. El token sirve **una sola vez** y caduca a la hora: si no vale, `status` es `RESET_PASSWORD_INVALID_TOKEN_ERROR`.

Al cambiar la contraseña **se revocan todas las sesiones del usuario**: los refresh tokens que tuviera una integración dejan de servir y hay que volver a iniciar sesión.

### Verificar el email

Al registrarse (`POST /auth/signup`), la API envía sola un email con un enlace a `<la aplicación web>/verify-email?token=…&tenantId=…`.

- `POST /auth/user/email/verify` con `{"method":"token","token":"<token del enlace>"}` lo verifica, sin necesidad de sesión. El token caduca en 24 horas y sirve una vez: si no vale, `status` es `EMAIL_VERIFICATION_INVALID_TOKEN_ERROR`.
- `GET /auth/user/email/verify` (con sesión) dice si está verificado: `{"status":"OK","isVerified":…}`.
- `POST /auth/user/email/verify/token` (con sesión) reenvía el enlace, o responde `EMAIL_ALREADY_VERIFIED_ERROR` si ya lo está.

La API funciona sin verificar el email. Las rutas que lo exijan responderán **403** con `code: email_not_verified`; hoy ninguna lo exige todavía.

### Capacidades de la instalación

`GET /api/v1/meta` es público y dice qué ofrece esta instalación. Hoy solo incluye `email_enabled`: con `false` no hay servidor de correo, y pedir la recuperación responde igual pero no envía nada.

## Errores

Los errores de la aplicación tienen siempre esta forma:

```json
{ "detail": "Application not found", "code": "not_found" }
```

`detail` es un texto para personas y puede cambiar. **`code` es estable**: úsalo para decidir qué hacer.

| HTTP | Cuándo | Ejemplos de `code` |
|---|---|---|
| 401 | Sin sesión, o el access token caducó | — (renueva y repite) |
| 404 | No existe, **o es de otro usuario** | `not_found` |
| 409 | La petición es válida, pero una regla la impide | `invalid_transition`, `company_in_use`, `company_name_taken`, `applications_limit_reached`, `companies_limit_reached`, `reminders_limit_reached`, `reminder_not_pending`, `cannot_undo_initial_change` |
| 422 | Datos que no cumplen las reglas de negocio | `changed_at_in_future`, `changed_at_before_last_change`, `applied_at_required`, `salary_range_invalid` |

Un recurso de otro usuario responde **404, igual que uno inexistente**: la API nunca confirma que un id exista si no es tuyo.

Los errores de **formato** (un campo obligatorio que falta, un tipo equivocado) también son 422, pero con la forma estándar de FastAPI: `detail` es una lista con la ubicación y el motivo de cada fallo, sin `code`.

## Listados

Los listados se paginan con `page` (desde 1) y `limit` (20 por defecto, 100 como máximo), y responden siempre con la misma forma:

```json
{ "items": [ ... ], "total": 57, "page": 1, "limit": 20, "pages": 3 }
```

Se ordenan con `sort_by` y `order` (`asc` o `desc`). Los campos por los que se puede ordenar y los filtros de cada listado están en su página de la referencia.

## Fechas

- Los instantes (`due_at`, `scheduled_at`, `changed_at`, `created_at`…) van en **ISO 8601 con zona horaria**, por ejemplo `2026-10-01T09:30:00Z`. Uno sin zona horaria se rechaza con 422.
- `applied_at` es un **día**, sin hora: `2026-10-01`.

## Estados y transiciones

El estado de una solicitud **no se cambia con `PATCH`**: tiene su propio endpoint (`POST /applications/{application_id}/status-changes`), que registra el cambio en el historial. Cada solicitud trae en `allowed_transitions` los estados a los que puede pasar desde el actual; cualquier otro se rechaza con `invalid_transition`.

## Límites

| Recurso | Límite por cuenta (por defecto) | Al superarlo |
|---|---|---|
| Solicitudes | 5000 | 409 `applications_limit_reached` |
| Empresas | 2000 | 409 `companies_limit_reached` |
| Recordatorios, en cualquier estado | 5000 | 409 `reminders_limit_reached` (borrar libera espacio: `DELETE /reminders/{id}`) |
| Notas | 5000 caracteres | 422 |

Los de cantidad pueden ser otros en cada instalación, e incluso en cada cuenta. `GET /api/v1/me/usage` dice los de la cuenta de la sesión, con lo usado y lo que queda. Al alcanzar uno, el 409 lleva además los números:

```json
{ "detail": "Limit reached: 2000 of 2000", "code": "companies_limit_reached", "limit": 2000, "used": 2000 }
```

## Llamadas desde un navegador

Por seguridad, la API solo acepta peticiones de navegador desde los orígenes configurados en la instalación (`CORS_ORIGINS`), que normalmente son solo los de la propia aplicación web. Una integración de servidor a servidor no se ve afectada.
