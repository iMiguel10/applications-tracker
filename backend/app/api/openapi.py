"""Metadatos del OpenAPI: la portada de /docs para quien integra con la API."""

API_TITLE = "Applications Tracker API"
API_VERSION = "0.1.0"

API_DESCRIPTION = """
API REST de **Applications Tracker**: seguimiento de solicitudes a puestos de trabajo.

## Autenticación

La autenticación la gestiona SuperTokens (email y contraseña). Hay dos modos, y la
API acepta los dos en todas las rutas protegidas:

| Cliente | Modo | Cómo |
|---|---|---|
| Navegador (la SPA) | Cookies httpOnly | Login con la cabecera `st-auth-mode: cookie`. El navegador envía las cookies solo. |
| Integraciones, scripts, Swagger | Bearer | Login con `st-auth-mode: header` (o sin esa cabecera). Se usa `Authorization: Bearer <st-access-token>`. |

### Probar desde esta página

1. Despliega **POST /auth/signin**, pulsa *Try it out* y ejecuta con un usuario existente.
2. En *Response headers*, copia el valor de `st-access-token`.
3. Pulsa **Authorize**, pega el token en *BearerAuth* y confirma.
4. Las rutas con candado ya se pueden ejecutar. El token caduca a los **5 minutos**: renuévalo con `POST /auth/session/refresh` o repite el login.

## Convenciones

- **Errores de validación:** 422, con el detalle de cada campo en `detail`.
- **Sin sesión:** 401 `{"message": "unauthorised"}`.
- **Recursos de otro usuario:** 404, igual que si no existieran.
- **Listados paginados:** `page` (desde 1) y `limit` (máximo 100) →
  `{items, total, page, limit, pages}`.
- **Fechas:** ISO 8601 en UTC.
"""

OPENAPI_TAGS = [
    {
        "name": "Autenticación",
        "description": "Registro, login, logout y renovación de sesión. Las sirve el "
        "middleware de SuperTokens: responden siempre 200 con el resultado en `status`, "
        "salvo `signout` y `refresh`, que responden 401 sin sesión.",
    },
    {
        "name": "Health",
        "description": "Estado de la API y de la base de datos. Público.",
    },
    {"name": "Me", "description": "Usuario de la sesión actual."},
    {"name": "Applications", "description": "Solicitudes a puestos de trabajo."},
]

SWAGGER_UI_PARAMETERS = {
    # Mantiene el token de "Authorize" al recargar /docs.
    "persistAuthorization": True,
}
