# Documentar y usar la API

Cómo se documenta la API, dónde se consulta, cómo se prueba desde Swagger y cómo se integra otro sistema con ella.

## Dónde está la documentación

La documentación de la API **es el esquema OpenAPI que genera FastAPI** a partir del código: rutas, schemas de Pydantic, descripciones y respuestas. No hay una documentación paralela escrita a mano.

| Dónde | Para qué |
|---|---|
| <http://localhost:8000/docs> | **Swagger UI** con la API en marcha: leer y **ejecutar** peticiones reales |
| <http://localhost:8000/redoc> | ReDoc: la misma información en formato de lectura |
| <http://localhost:8000/openapi.json> | El esquema en crudo, para generar clientes o importarlo en Postman/Insomnia |
| [Referencia de la API](../referencia/api.md) de este sitio | Copia versionada (`docs/referencia/openapi.json`), de solo lectura, disponible sin levantar la API |

## Autenticarse

La API acepta dos modos en todas las rutas protegidas ([decisión 0003](../decisiones/0003-autenticacion-por-cookie-y-bearer.md)):

| Cliente | Modo | Login con |
|---|---|---|
| Navegador (la SPA) | Cookies httpOnly | `st-auth-mode: cookie` (lo envía el SDK `supertokens-web-js`) |
| Swagger, scripts, integraciones | `Authorization: Bearer` | `st-auth-mode: header`, o sin esa cabecera |

### Desde Swagger

1. En <http://localhost:8000/docs>, despliega **POST /auth/signin**, pulsa *Try it out* y luego *Execute*. El cuerpo de ejemplo ya trae un usuario de desarrollo.
2. En *Response headers*, copia el valor de **`st-access-token`**.
3. Pulsa **Authorize** (arriba a la derecha), pega el token en **BearerAuth** y confirma. Swagger lo recuerda aunque recargues la página.
4. Las rutas con candado ya se pueden ejecutar. El *curl* que muestra Swagger incluye la cabecera, listo para copiar.

El access token **caduca a los 5 minutos** ([decisión 0002](../decisiones/0002-access-token-de-5-minutos.md)). Cuando las peticiones empiecen a responder 401, repite el login, o renueva el token con `POST /auth/session/refresh` enviando el **refresh token** como Bearer.

### Desde una integración

```bash
# 1. Login en modo cabecera: los tokens llegan en las cabeceras de respuesta
curl -si -X POST http://localhost:8000/auth/signin \
  -H 'Content-Type: application/json' -H 'st-auth-mode: header' \
  -d '{"formFields":[{"id":"email","value":"ana@example.com"},{"id":"password","value":"secreto123"}]}'
#    → st-access-token: eyJ...   st-refresh-token: tOb...

# 2. Llamadas a la API con el access token
curl -s http://localhost:8000/api/v1/me -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Al recibir 401, renovar con el refresh token (devuelve un par NUEVO)
curl -si -X POST http://localhost:8000/auth/session/refresh \
  -H 'st-auth-mode: header' -H "Authorization: Bearer $REFRESH_TOKEN"

# 4. Cerrar sesión
curl -s -X POST http://localhost:8000/auth/signout -H "Authorization: Bearer $ACCESS_TOKEN"
```

> **Trampa — el refresh token solo vale una vez.** Cada `POST /auth/session/refresh` devuelve **también un refresh token nuevo**, y el anterior queda invalidado. Si una integración guarda el primero y lo reutiliza, SuperTokens interpreta el reúso como un **robo de token** y revoca la sesión entera. Lo mismo pasa si dos procesos de la misma integración refrescan a la vez con el mismo token. Regla: tras cada refresco, sustituir los **dos** tokens guardados, y que refresque un solo proceso cada vez.

Las respuestas de `/auth/signup` y `/auth/signin` son **siempre 200**: el resultado va en `status` (`OK`, `WRONG_CREDENTIALS_ERROR`, `FIELD_ERROR`). Una integración debe comprobar `status`, no el código HTTP.

## Cómo se documenta un endpoint

Todo lo que aparece en `/docs` sale del código. Al crear o cambiar un endpoint, cada punto de esta lista tiene su sitio:

| Qué | Dónde | Ejemplo |
|---|---|---|
| Grupo en Swagger | `tags` del router, con su descripción en `OPENAPI_TAGS` (`app/api/openapi.py`) | `tags=["Applications"]` |
| Título corto | `summary=` del decorador | `summary="Crear una solicitud"` |
| Explicación | **Docstring** del handler: se publica como `description`. Se escribe para quien consume la API, no para quien mantiene el código. | Qué hace, reglas visibles, casos especiales |
| Cuerpo y respuesta | Tipos de Pydantic: parámetro del cuerpo y **anotación de retorno** (`-> ApplicationRead`) | FastAPI deduce el `response_model` de la anotación |
| Campos | `Field(description=..., examples=[...])` en el schema. Las restricciones (`min_length`, `le`…) se publican solas. | `examples=["Backend Developer"]` |
| Parámetros de consulta | `Query(description=...)` | `limit: int = Query(20, le=100, description=...)` |
| Código de éxito | `status_code=` si no es 200 | `status.HTTP_201_CREATED` |
| Errores | `responses={404: {"model": ..., "description": ...}}`. El **401** ya lo declara el router `protected` para todas sus rutas. | 404 si no existe, 409 si una regla lo impide |
| Seguridad | Nada: incluir el router en `protected` (`app/api/v1/router.py`) añade el candado y el 401 | — |

Lo que **no** va en la documentación de la API: detalles internos (tablas, services, invariantes). Eso está en la [arquitectura](../arquitectura/index.md).

Dos pruebas hacen cumplir estas convenciones:

- `test_every_operation_has_a_summary_and_a_description`: ninguna operación llega a `/docs` sin `summary` ni docstring.
- `test_exported_openapi_reference_matches_the_api`: la copia versionada coincide con la app (ver abajo).

## Regenerar la referencia versionada

`docs/referencia/openapi.json` es la copia del esquema que publica este sitio. Tras cambiar cualquier endpoint o schema:

```bash
docker compose exec api python -m app.scripts.export_openapi
```

El fichero se regenera y se incluye **en el mismo commit** que el cambio. Si se olvida, `test_exported_openapi_reference_matches_the_api` falla con el comando exacto para arreglarlo: la referencia publicada no puede quedar desactualizada sin que se note.

> **Por qué `docs/referencia` está montado en el contenedor `api`** (en `/reference`): el script corre dentro del contenedor, que es donde está la app, y escribe directamente en la carpeta del sitio. `compose.test.yml` monta la misma carpeta en solo lectura para el test de sincronía.

## Las rutas `/auth/*`

Las sirve el middleware de SuperTokens y no pasan por el router de FastAPI, así que no aparecerían en el OpenAPI por sí solas. `app/api/auth_docs.py` las declara **solo para documentarlas**:

- Sus schemas (`app/schemas/auth.py`) se escribieron a partir de respuestas reales del SDK.
- Sus handlers nunca se ejecutan, porque el middleware responde antes. Si algún día se ejecutaran, responden 500, y las pruebas de humo de auth fallan.
- **Al actualizar `supertokens-python`**, revisar que el contrato de estas rutas no ha cambiado (estados de `status`, cabeceras) y ajustar sus schemas.
