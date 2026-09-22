# 0003 — Autenticación por cookie y también por Bearer

- **Fecha:** 2026-09-22
- **Estado:** aceptada

## Contexto

En F1, el backend fijaba `get_token_transfer_method` a `"cookie"`: solo aceptaba sesiones por cookies httpOnly. Para el navegador es lo correcto, pero deja fuera dos casos:

- **Integraciones** con otros sistemas: scripts, servicios o clientes que no son un navegador. Gestionar cookies fuera de un navegador es poco habitual; el mecanismo esperado es `Authorization: Bearer`.
- **Probar la API desde Swagger** (`/docs`). Swagger no puede fijar cookies a mano, y el botón *Authorize* solo funciona con esquemas como Bearer.

## Decisión

El backend acepta los dos modos, que es el comportamiento por defecto de SuperTokens (se elimina la restricción):

- Un login con `st-auth-mode: cookie` devuelve los tokens en cookies httpOnly.
- Con `st-auth-mode: header`, o **sin esa cabecera**, los devuelve en las cabeceras de respuesta `st-access-token` y `st-refresh-token`, y se usan como `Authorization: Bearer`.
- Al verificar, cualquier ruta protegida acepta cualquiera de los dos.

El frontend fija `tokenTransferMethod: "cookie"` de forma **explícita** en `Session.init`. Es el valor por defecto de `supertokens-web-js`, pero ahora que el backend acepta cabeceras, la garantía de que el navegador nunca maneja tokens no debe depender de un valor por defecto.

El OpenAPI declara los esquemas `BearerAuth` y `CookieAuth` y documenta las rutas `/auth/*` (guía [Documentar y usar la API](../guias/documentar-la-api.md)).

## Alternativas descartadas

- **Solo cookies**: Swagger funcionaría haciendo login desde la propia página (mismo origen, así que el navegador reenvía la cookie), pero las integraciones tendrían que manejar cookies. Tampoco habría botón *Authorize*.
- **Solo Bearer también en el navegador**: el token quedaría accesible a JavaScript, y cualquier XSS podría robarlo. Las cookies httpOnly existen precisamente para evitarlo (RNF-01).
- **Un mecanismo aparte para integraciones (API keys propias)**: otra superficie de autenticación que diseñar, almacenar, rotar y revocar. SuperTokens ya da tokens con caducidad, rotación y revocación.

## Consecuencias

- Un login **sin** `st-auth-mode` devuelve cabeceras y **no** cookies. Cualquier cliente de navegador que no use el SDK debe enviar `st-auth-mode: cookie`.
- Las integraciones deben gestionar la **rotación del refresh token**: cada refresco devuelve uno nuevo, y reutilizar el anterior revoca la sesión (trampa documentada en la guía).
- `CORS` ya expone las cabeceras de tokens (`access-control-expose-headers`), porque las añade el middleware de SuperTokens. Una SPA de otro origen en modo cabecera podría leerlas; hoy ninguna lo hace.
