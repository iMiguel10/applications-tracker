# 0002 — Access token de 5 minutos

- **Fecha:** 2026-09-22
- **Estado:** aceptada

## Contexto

El diseño de autenticación (prueba T7) suponía que el logout invalidaba la sesión al momento. Al implementar F1 se comprobó que no es del todo así:

1. Se inicia sesión y se copian las cookies (como haría quien las robase).
2. Se cierra sesión.
3. Con las cookies copiadas, `GET /api/v1/me` sigue respondiendo **200**; `POST /auth/session/refresh` responde **401**.

El motivo: el access token es un JWT firmado y `verify_session()` lo valida comprobando firma y caducidad **sin consultar al core**, que es lo que la hace rápida. El logout revoca el refresh token (la sesión no puede renovarse), pero un access token ya emitido sigue siendo válido hasta que caduca. Con la configuración por defecto del core, eso puede ser **hasta 1 hora**.

## Decisión

El core emite access tokens de **5 minutos** (`ACCESS_TOKEN_VALIDITY: 300` en el servicio `supertokens`, también en `compose.test.yml`). El SDK del frontend los refresca solo cuando caducan, sin que el usuario lo note.

Tras un logout, una copia del access token deja de servir en 5 minutos como máximo. La prueba T7 comprueba lo que sí es inmediato: que el refresh token queda revocado.

## Alternativas descartadas

- **`verify_session(check_database=True)`**: revocación inmediata, pero cada petición autenticada hace una llamada de red al core, y el core pasa a ser imprescindible incluso para leer. Para una aplicación de uso personal, 5 minutos de ventana no justifican ese coste en todas las peticiones.
- **Dejar la hora por defecto**: una hora de validez para una sesión cerrada o robada es una ventana demasiado grande a cambio de nada, porque acortarla es una sola variable.

## Consecuencias

- El frontend hace un `POST /auth/session/refresh` cada 5 minutos de uso activo. Es barato y lo gestiona el SDK, que coordina el refresco entre pestañas.
- Si en el futuro hiciera falta revocación inmediata (por ejemplo, "cerrar sesión en todos los dispositivos" tras un robo), el cambio es pasar `check_database=True` solo en esa dependencia o en endpoints sensibles.
- Medido en F1: el token emitido tiene `exp - iat = 290 s`. El core resta un pequeño margen a los 300 configurados.
