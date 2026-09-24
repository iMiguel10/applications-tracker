# Servicios y estructura

> Estado: **v1 construida; ampliación v2 en diseño (§8)** · Fecha: 2026-09-22 · Depende de la [arquitectura](index.md)
>
> Convenciones heredadas de `task-manager-api` (backend y Docker) y `frontend_gestpro` (frontend), analizados el 2026-09-21.
> Las desviaciones van marcadas como **[nuevo]**.

## 1. Servicios

| Servicio | Imagen u origen | Puerto en el host | Para qué | Fase |
|---|---|---|---|---|
| `db` | `postgres:17` | 5432 | Datos de la aplicación (gestionados con Alembic) | ✔ existe |
| `api` | `./backend` (python 3.12 + uv) | 8000 | API FastAPI; hace de proxy de `/auth/*` hacia SuperTokens | ✔ existe |
| `frontend` | `./frontend/Dockerfile.dev` (node 24) | 5173 | SPA con Vite y HMR | ✔ existe |
| `docs` | `squidfunk/mkdocs-material:9` | 8001 | Este sitio, con recarga en vivo | ✔ existe |
| `supertokens-db` | `postgres:17` | — | Base de datos exclusiva del core de SuperTokens | ✔ existe (F1) |
| `supertokens` | `supertokens/supertokens-postgresql:12.2.0` (versión fijada) | — | Core de autenticación: usuarios, contraseñas, sesiones | ✔ existe (F1) |
| `mailpit` | `axllent/mailpit` | 8025 (UI) | Captura los emails en desarrollo | `[C]` Llega con la recuperación de contraseña o el canal de email |
| `api-test`, `db-test` | como `api` y `db` | — | Suite de pytest contra una BD aislada (`compose.test.yml`) | ✔ existe |

Aclaraciones:

- **`db` y `supertokens-db` son dos instancias con la misma imagen** (decisión A11). Así Alembic nunca ve las tablas de SuperTokens y cada BD se puede respaldar o resetear por separado.
- **El core de SuperTokens no publica puerto.** Solo `api` habla con él por la red interna de Docker (`http://supertokens:3567`). El navegador nunca lo ve.
- **`mailpit` está considerado pero no se añade** hasta que algo envíe emails. Meterlo antes es un servicio que arranca sin usarse.

Fragmento de `compose.yml` con los servicios de auth (añadidos en F1). Se conservan los detalles heredados: healthchecks, `depends_on` con `service_healthy` y volúmenes con nombre. `supertokens-db` **no** usa `env_file: .env`: con él tomaría `POSTGRES_DB`/`POSTGRES_USER` de la app y crearía la misma base de datos.

```yaml
  supertokens-db:
    image: postgres:17
    environment:
      POSTGRES_DB: ${SUPERTOKENS_DB_NAME}
      POSTGRES_USER: ${SUPERTOKENS_DB_USER}
      POSTGRES_PASSWORD: ${SUPERTOKENS_DB_PASSWORD}
    volumes:
      - supertokens_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 5

  supertokens:
    image: supertokens/supertokens-postgresql:12.2.0   # debe implementar la CDI del SDK
    environment:
      POSTGRESQL_CONNECTION_URI: postgresql://${SUPERTOKENS_DB_USER}:${SUPERTOKENS_DB_PASSWORD}@supertokens-db:5432/${SUPERTOKENS_DB_NAME}
      API_KEYS: ${SUPERTOKENS_API_KEY}
      ACCESS_TOKEN_VALIDITY: 300   # decisión 0002
    depends_on:
      supertokens-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/127.0.0.1/3567 && echo -e \"GET /hello HTTP/1.1\\r\\nhost: 127.0.0.1\\r\\nConnection: close\\r\\n\\r\\n\" >&3 && cat <&3 | grep Hello'"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    depends_on:
      db:
        condition: service_healthy
      supertokens:
        condition: service_healthy
```

> **Trampa — los volúmenes de dependencias no se actualizan al reconstruir.**
>
> - **Backend.** `api_venv` es un volumen con nombre. Docker lo rellena con el `.venv` de la imagen **solo la primera vez** que lo crea. Si se añade una dependencia y se reconstruye la imagen, el contenedor sigue montando el volumen viejo, sin el paquete nuevo, y falla con `ModuleNotFoundError`. La imagen, que sí lo tiene, parece correcta.
> - **Frontend.** Con `/app/node_modules`, el volumen anónimo, pasa lo mismo: `docker compose up --build` reutiliza el volumen anónimo del contenedor anterior.
> - **Solución.** Instalar siempre las dependencias **dentro del contenedor en marcha, con `exec`**: `docker compose exec api uv add …` y `docker compose exec frontend npm install …`. Así se actualizan a la vez el volumen que usa el contenedor y el `package.json`/`pyproject.toml` del host, por el bind mount. Después de un `git pull` que cambie dependencias, usar `docker compose up --build -V`: `-V` renueva los volúmenes anónimos, y además `docker compose run --rm api uv sync` para el volumen con nombre.
> - **[nuevo] No usar `docker compose run --rm frontend npm install`**, que era la convención heredada de GestPro. `run` crea un contenedor **nuevo** con su propio volumen anónimo de `node_modules`: el paquete se instala ahí y se descarta al terminar. El contenedor `frontend` en marcha nunca lo recibe y Vite falla al importarlo. Solo cambian `package.json` y `package-lock.json`, así que parece que la instalación funcionó.

## 2. Estructura del repositorio

```
applications-tracker/
├── compose.yml                 desarrollo (db, api, frontend, docs; F1: supertokens, supertokens-db)
├── compose.test.yml            pytest contra BD aislada
├── .env.example                plantilla de variables (.env y .env.test no se versionan)
├── mkdocs.yml
├── docs/                       este sitio (fuente en Markdown)
├── backend/
├── frontend/
├── .github/workflows/          CI (F6)
├── .claude/agents/             agentes de apoyo: documentador, verificador
├── CLAUDE.md                   guía de trabajo del repositorio
└── README.md                   escaparate
```

**[nuevo]** Monorepo con backend, frontend y docs juntos. En los proyectos previos el frontend y el backend eran repositorios separados. Aquí comparten `compose.yml`, `.env` y la documentación, y un cambio que cruza la API cabe en un solo commit.

## 3. Backend

```
backend/
├── Dockerfile, entrypoint.sh   imagen (uv) · aplica migraciones y arranca
├── pyproject.toml, uv.lock     dependencias y configuración de ruff, mypy y pytest
├── alembic.ini, migrations/    migraciones (una por cambio de esquema, revisadas a mano)
├── app/
│   ├── main.py                 crea la app: routers, CORS, middleware de SuperTokens, handlers
│   ├── core/
│   │   ├── config.py           Settings (pydantic-settings) desde variables de entorno
│   │   ├── exceptions.py       AppException y subclases de dominio (NotFound, Conflict…)
│   │   ├── exception_handlers.py
│   │   ├── logging.py
│   │   └── supertokens.py      init() del SDK (F1)
│   ├── db/
│   │   ├── base.py             DeclarativeBase y convención de nombres de constraints
│   │   └── session.py          engine async, get_db
│   ├── domain/                 [nuevo] reglas puras, sin I/O: enums y tabla de transiciones
│   │   └── application_status.py
│   ├── models/                 tablas SQLAlchemy, una por fichero
│   ├── schemas/                modelos Pydantic de entrada y salida, uno por recurso
│   ├── repositories/           [nuevo] todo el acceso a almacenes de datos
│   │   ├── application_repository.py
│   │   ├── user_repository.py      get_or_create idempotente (F1)
│   │   └── identity_repository.py  único punto que consulta usuarios al SDK de SuperTokens (F1)
│   ├── services/               reglas de negocio y transacciones
│   │   ├── application_service.py
│   │   ├── application_status_service.py
│   │   └── notifications/      NotificationChannel + InAppChannel (F4)
│   └── api/v1/
│       ├── router.py           routers públicos + `protected` (exige sesión por construcción)
│       ├── deps.py             get_db, get_current_user, fábricas de services
│       └── endpoints/          un fichero por recurso
└── tests/
    ├── conftest.py             cliente, sesión con rollback por prueba, usuarios de prueba
    ├── api/  services/  repositories/  domain/
```

### Reglas de capas

| Capa | Puede | No puede |
|---|---|---|
| `endpoints/` | Declarar rutas, validar con `schemas/`, obtener dependencias (`Depends`), llamar a **un** service y devolver un schema | Importar `repositories/` o `models/` para consultar · ejecutar SQL · contener reglas de negocio · hacer `commit` |
| `services/` | Aplicar reglas de negocio, usar `domain/`, llamar a repositories, **abrir y confirmar la transacción** (`commit`/`rollback`) y lanzar excepciones de `core/exceptions.py` | Importar FastAPI (`HTTPException`, `Request`, `Depends`) · construir consultas SQL · conocer códigos HTTP |
| `repositories/` | Construir y ejecutar consultas SQLAlchemy, `add`/`flush`/`delete`, recibir `user_id` y filtrar por él | Hacer `commit` · decidir reglas de negocio · lanzar excepciones HTTP · exponer métodos sin `user_id` sobre datos de usuario |
| `domain/` | Enums, tablas de reglas y funciones puras (`allowed_transitions(status)`) | Cualquier I/O: BD, red, sesión, configuración |
| `models/` | Declarar tablas, relaciones y constraints | Contener lógica |
| `schemas/` | Validar forma y formato de los datos de entrada y salida | Acceder a la BD · reglas que dependan de otros datos (eso es del service) |

**La regla que lo resume:** *si algo habla con la base de datos, vive en `repositories/`; si algo decide, vive en `services/` o `domain/`.*

Dirección de dependencias: `endpoints → services → repositories → models`, y `domain` puede usarse desde `services` y `schemas`. Nunca al revés.

### Convenciones

| Tema | Convención | Origen |
|---|---|---|
| Estructura `api/v1/endpoints`, `core`, `db`, `models`, `schemas`, `services` | Igual que la plantilla | Heredado |
| Paginación | `page` + `limit` (máx. 100) → `{items, total, page, limit, pages}` | Heredado |
| Ordenación | `sort_by` + `order` validados contra una lista blanca de columnas | Heredado |
| Errores | `AppException` → `{"detail": …}`, con handler genérico para los 500 | Heredado |
| Services y repositories | **[nuevo]** **Clases** que reciben la `AsyncSession` en el constructor; `deps.py` las construye por petición. Así service y repositories comparten la sesión y, por tanto, la transacción. | La plantilla usaba funciones sueltas que recibían `db` |
| Códigos de error | **[nuevo]** `AppException` lleva un `code` estable (`not_found`, `invalid_transition`, `company_in_use`…) y la respuesta es `{"detail", "code"}`. El frontend traduce por `code`, nunca por el texto. | La plantilla solo devolvía `detail` |
| Fechas | **[nuevo]** `DateTime(timezone=True)`; `created_at` con `server_default=func.clock_timestamp()`, nunca `now()` ([decisión 0001](../decisiones/0001-clock-timestamp-en-created-at.md)) | La plantilla usaba `DateTime` naive y quitaba el UTC a mano |
| Ids | **[nuevo]** `UUID`, con `server_default=text("gen_random_uuid()")` | La plantilla usaba enteros |
| Nombres de constraints | **[nuevo]** `MetaData(naming_convention=…)` en `db/base.py`, para que Alembic genere nombres deterministas y las migraciones de `CHECK` y FK se puedan revertir | No existía |
| Nombres | Fichero `application_repository.py` → clase `ApplicationRepository`; schemas `ApplicationCreate`, `ApplicationUpdate`, `ApplicationRead`, `ApplicationList` | Heredado y ampliado |
| Calidad | `ruff check`, `ruff format`, `mypy app tests` (con el plugin de pydantic) sin errores | Heredado; el plugin es **[nuevo]** |
| Migraciones | **[nuevo]** `migrations/env.py` importa `app.models`, y `models/__init__.py` importa cada modelo: un modelo no importado es invisible para autogenerate, que generaría un `drop_table`. Un *post-write hook* de Alembic pasa `ruff check --fix` y `ruff format` a cada migración generada. | En la plantilla `env.py` no importaba los modelos |
| Log de SQL | **[nuevo]** En desarrollo, nivel INFO del logger `sqlalchemy.engine` en `core/logging.py`, **no** `create_engine(echo=True)`, que añade su propio handler y duplica cada línea | La plantilla usaba `echo=True` |
| Tests | **[nuevo]** `tests/conftest.py`: engine con `NullPool` (un event loop por test) y sesión dentro de una transacción externa con `join_transaction_mode="create_savepoint"`. El `commit()` de los services solo confirma un savepoint y todo se revierte al acabar. `get_db` se sustituye con `dependency_overrides`. | La plantilla hacía commits reales y `engine.dispose()` por test |
| Consultas | **[nuevo]** `eager_defaults=True` en `Base`: los valores que calcula la BD (`updated_at`) se leen con `RETURNING` también en los `UPDATE`; sin ello, leerlos en async falla con `MissingGreenlet`. Relaciones con `lazy="raise"`: cada consulta declara lo que carga (`joinedload`, o `contains_eager` si ya hay `join`). | No existía |
| Búsquedas | **[nuevo]** `ILIKE` siempre con `repositories/search.py:contains_pattern()` y `escape=LIKE_ESCAPE`: sin escapar, `%` y `_` del usuario actúan como comodines | La plantilla usaba `f"%{search}%"` |
| PATCH | **[nuevo]** Schemas `*Update` con todo opcional y `model_dump(exclude_unset=True)`: "no enviado" no toca el campo, `null` lo vacía. Las reglas entre campos (rango salarial, `applied_at` obligatoria) se validan en el service **sobre los valores mezclados** con lo guardado, porque el schema solo ve lo enviado. | La plantilla tenía PUT y PATCH separados |
| Enumerados | **[nuevo]** `db/constraints.py:enum_check()` genera el `CHECK` desde el `StrEnum` de `domain/`. En las migraciones, en cambio, los valores se **congelan como texto**: una migración describe el esquema de su momento. | No existía |
| Validación de texto | **[nuevo]** Normalizar (mayúsculas, recortes) con `BeforeValidator`, no con `StringConstraints(to_upper=True)`: Pydantic comprueba el `pattern` **antes** de `to_upper`. Se aplicó a la moneda del salario mientras fue texto libre validado por regex; desde F8 esa columna es un enum cerrado (`Currency`, R5) y ya no lo necesita, pero la convención queda anotada para el próximo campo de texto libre que sí lo requiera | — |
| Errores de negocio | **[nuevo]** `NotFoundError` (404 `not_found`), `ConflictError` (409 con `code`), `LimitReachedError` (409 `<recurso>_limit_reached`) y `AppException(status_code=422, code=...)` para reglas entre campos | La plantilla solo tenía `AppException` sin código |

> **Fallos encontrados en la plantilla**, anotados de paso; ya se corrigieron en este proyecto al copiarla:
>
> - `main.py` pasaba `settings.cors_origins` (un `str`) a `allow_origins` en lugar de `cors_origins_list`.
> - El `.dockerignore` estaba en la raíz, pero el contexto de build es `./backend`, así que no se aplicaba.
> - `/app` y `.venv` pertenecían a root, lo que impedía a `appuser` escribir la caché de pytest o ejecutar `uv add`.
> - mypy daba 3 errores (faltaba el plugin de pydantic, y el handler tenía una firma incompatible con Starlette).

## 4. Frontend

```
frontend/src/
├── main.tsx, App.tsx          importa PRIMERO shared/lib/supertokens; QueryClient + RouterProvider + Toaster
├── app/providers/             ThemeProvider (F8.4): tema claro/oscuro en localStorage, no en el backend — la sesión sigue gestionándola el SDK y TanStack Query (ver autenticación §4)
├── features/
│   ├── auth/                  login, registro, logout, /me; lib/safeRedirect (F1)
│   ├── companies/             (F2)
│   ├── applications/          solicitudes + cambios de estado (F2, F3)
│   ├── interviews/            (F4)
│   ├── reminders/             (F4)
│   ├── dashboard/             (F5)
│   └── health/                página temporal de la Fase 1; se retira cuando exista el dashboard
├── pages/                     una página por ruta
├── routes/                    Router.tsx + AuthLoaders.ts
├── shared/
│   ├── components/{ui,form,layout}
│   │   └── common/            EmptyState, ErrorState, Skeletons, PageFallback, Pagination, SearchInput (F8)
│   ├── config/navigation.ts
│   ├── hooks/                 useDebounce, useDocumentTitle (F8)
│   ├── i18n/                  i18n.ts + locales/{es,en}.json
│   └── lib/                   apiClient.ts, queryClient.ts, supertokens.ts (F1), utils.ts
├── styles/global.css
└── test/setup.ts
```

Cada feature sigue la estructura heredada:

```
features/<feature>/
├── types/            tipos de dominio (lo que devuelve la API)
├── schemas/          zod + tipos inferidos *FormValues; los mensajes son claves de i18n
├── services/         <feature>.service.ts: única capa que usa apiClient
├── <feature>.keys.ts factory de query keys: all → lists() → list(params) → details() → detail(id)
├── hooks/queries/    un useQuery por lectura
├── hooks/mutations/  un useMutation por escritura, que invalida las keys afectadas
└── components/
```

**Patrón obligatorio para una feature nueva, en orden:** `types/` → `schemas/` → `services/` → `<feature>.keys.ts` → `hooks/queries` y `hooks/mutations` → `components/` → página en `pages/` → ruta en `routes/Router.tsx` → entrada en `shared/config/navigation.ts` → claves en `es.json` **y** `en.json`.

### Reglas de capas

| Capa | Puede | No puede |
|---|---|---|
| `services/` | Llamar a `apiClient` y transformar la respuesta | Usar React, hooks o estado |
| `hooks/` | Usar TanStack Query sobre los services e invalidar keys | Llamar a `fetch` o `apiClient` directamente |
| `components/`, `pages/` | Usar hooks, formularios de `shared/components/form` y UI de `shared/components/ui` | Importar services, llamar a la API o duplicar reglas de negocio del backend (p. ej., transiciones) |

### Adaptaciones respecto a `frontend_gestpro`

| Tema | En GestPro | Aquí |
|---|---|---|
| Acceso a datos | `services/` llaman a Supabase | `services/` llaman a `shared/lib/apiClient.ts` (`fetch` + `credentials: "include"` desde F1) |
| Sesión | `supabase.auth` + `onAuthStateChange` | `supertokens-web-js` (`Session.doesSessionExist`, refresco automático de la sesión) |
| Roles | `user`/`manager`/`admin` y filtrado de menús por rol | Un solo rol: `NavItem` sin `roles` |
| Errores | Mensajes de Supabase | `ApiError` con `status` y `code`, traducido con la clave `errors.<code>` |
| Filtros de listados | Estado local | Parámetros de la URL (decisión A16). Cada listado tiene funciones **puras** `parse`/`serialize` (p. ej. `features/applications/lib/listParams.ts`) que descartan valores desconocidos: un enlace viejo o escrito a mano nunca rompe la página ni llega a la API como 422. Se prueban sin montar componentes. |
| Módulo genérico `tracking` | Factory para 5 módulos idénticos | No aplica: no hay entidades con la misma forma |
| Tipos | Escritos a mano en `types/` | Igual: a mano. Ver la decisión cerrada 9. |
| Utilidad `cn` | `clsx` + `tailwind-merge` en `shared/lib/utils.ts` | **[nuevo]** shadcn 4.2x genera los componentes con `import { cn } from "cn"`, el paquete oficial `shadcn-ui/cn`. `shared/lib/utils.ts` lo reexporta para que el código propio siga importando de `@/shared/lib/utils`; `clsx` y `tailwind-merge` se eliminan. |
| ESLint en `ui/` | Sin excepción: `npm run lint` fallaba por `buttonVariants` | **[nuevo]** `react-refresh/only-export-components` desactivada solo en `src/shared/components/ui/**`, que es código generado y no se edita |
| Tipo `Page<T>` | No existía | **[nuevo]** `shared/types/Page.ts`, espejo de `schemas/pagination.py` |
| Combobox asíncrono | `FormAsyncCombobox` con estado propio y `fetch` en un efecto | **[nuevo]** Carga las opciones con `useQuery` (prop `queryKey`, que conviene colgar de la key de la feature para que se refresque al invalidarla) y admite `onCreate` para crear el elemento sin salir del formulario (RF-13) |
| Fechas sin hora | `Date` en el formulario y `toDateOnlyString` al enviar | **[nuevo]** El formulario guarda el texto `"yyyy-MM-dd"` de la API. `shared/lib/dates.ts` (`parseDateOnly`/`toDateOnly`) lo convierte con fecha **local**: `new Date("2026-09-01")` es medianoche UTC y, al oeste de UTC, el día anterior |
| Selects opcionales | Sin opción vacía | **[nuevo]** `FormSelect` con `emptyLabel`: guarda `null`, no `""` |
| Popover / Dialog | `asChild` (Radix) | Base UI usa la prop `render`: `asChild` no hace nada y anida un botón dentro de otro |
| Errores de la API en formularios | Aviso genérico | **[nuevo]** `errorMessageKey(error)` traduce por `code` (`errors.<code>`); si el código corresponde a un campo, se marca el campo con `setError` |
| Estados de carga, vacío y error | Cada página los repetía a mano | **[nuevo] (F8)** `shared/components/common/{Skeletons,EmptyState,ErrorState}.tsx`, reutilizados en toda página que liste o cargue un recurso. Un 404 no es un error de red: `features/applications/components/ApplicationLoadError.tsx` lo distingue (invariante 2, recurso ajeno = inexistente) y ofrece volver al listado en vez de un botón de reintentar que nunca arreglaría nada |
| Reintentos de TanStack Query | Los 4 intentos por defecto de la librería, también ante un 4xx | **[nuevo] (F8)** `shared/lib/queryClient.ts`: un 4xx no se reintenta (no se arregla insistiendo); solo los fallos de red o 5xx, y una sola vez |

Se mantienen tal cual: shadcn/ui (`base-nova`) en `shared/components/ui` (añadidos con el CLI, nunca a mano), los wrappers de formulario de `shared/components/form`, el alias `@/`, i18n con claves y la configuración de TanStack Query.

> **Fallo encontrado en la plantilla:** el `vite.config.ts` de GestPro declara `setupFiles: ["./src/test/setup.ts"]`, pero ese fichero no existe, así que el primer test que se escriba fallará al arrancar Vitest. Aquí sí se creó.

## 5. Decisiones cerradas

Confirmadas con el usuario durante el diseño:

| # | Decisión | Regla derivada |
|---|---|---|
| 1 | Monorepo con git desde el inicio | Commits por fase, con código y documentación en el mismo commit |
| 2 | SuperTokens con **su propia instancia** de Postgres | Alembic solo gestiona la BD `db` |
| 3 | Login con email y contraseña | Sin recetas ThirdParty ni Passwordless en el MVP |
| 4 | `users` es solo un enlace, sin email | Los datos de identidad se piden a SuperTokens cuando hacen falta |
| 5 | Se mantiene `last_activity_at` | La actualizan los services al cambiar de estado y al tocar entrevistas |
| 6 | Se mantiene `changed_at` en el historial | El orden y deshacer usan `seq` ([0004](../decisiones/0004-secuencia-para-ordenar-el-historial.md)); las métricas usan `changed_at` y `created_at` queda como dato informativo |
| 7 | Recordatorios solo en la app, preparados para email y otros canales | `channel` + `NotificationChannel`; sin worker en el MVP |
| 8 | Documentación con MkDocs Material 9 | Imagen fijada; diagramas Mermaid |
| 9 | Tipos del frontend escritos a mano (heredado) | Generarlos desde OpenAPI (`openapi-typescript`) queda como mejora si aparecen divergencias. Riesgo aceptado: un cambio de schema en el backend no rompe la compilación del frontend. |
| 10 | Idioma | Identificadores de código en inglés; UI, comentarios, documentación y commits en español (heredado de GestPro) |
| 11 | Formato de commits | **[nuevo]** `tipo: descripción` (`feat`, `fix`, `docs`, `chore`, `test`, `refactor`), en lugar de `[TIPO]` de `task-manager-api`, porque es el formato que entienden las herramientas de changelog |

## 6. Documentación

Estructura del sitio:

| Sección | Contenido | Cuándo se llena |
|---|---|---|
| `producto/` | Especificación funcional | Ya |
| `arquitectura/` | Decisiones, modelo de datos, servicios y estructura, temas transversales (autenticación) | Ya |
| `guias/` | Cómo hacer cosas: crear una feature, añadir una migración, depurar la sesión | Con el código que describen |
| `referencia/` | API (generada), modelo de datos real y variables de entorno | Con el código que describen |
| `decisiones/` | Bitácora de cambios de rumbo | Cuando ocurran |

Las tres reglas contra el envejecimiento:

1. **La referencia de la API no se escribe a mano.** En F2 se añade un script que exporta `openapi.json` desde la app y lo publica en `referencia/`. El CI comprueba que el fichero exportado está al día.
2. **Los diagramas son texto** (Mermaid), revisables en el diff.
3. **La documentación cambia en el mismo commit que el código.** Si se aplaza, no se hace.

**README frente a sitio.**
- El `README.md` es el escaparate: qué resuelve, una captura, las decisiones destacadas y cómo arrancarlo con un comando. Se lee en dos minutos.
- Este sitio es la referencia para quien trabaja dentro.
- Nada se duplica entre los dos: el README enlaza aquí.

## 7. Integración continua (F6)

`.github/workflows/ci.yml` corre en cada `push` y `pull_request` contra `main`, con `concurrency` para cancelar la ejecución anterior del mismo ref. Cuatro jobs independientes:

| Job | Qué hace | Por qué así |
|---|---|---|
| `backend-lint` | `uv sync --frozen`, `ruff check`, `ruff format --check`, `mypy app tests` | Nativo con `astral-sh/setup-uv`, **sin Docker**: es el feedback más rápido y no necesita levantar contenedores para detectar un error de tipos o de estilo |
| `backend-tests` | `compose.test.yml` completo (`api-test`, `db-test`, SuperTokens de prueba…), la suite de pytest | **Con Docker Compose**, para tener paridad exacta con desarrollo: misma imagen, mismas migraciones al arrancar, el core real de SuperTokens (necesario para la prueba de humo T7) |
| `frontend` | `npm ci`, eslint, `tsc -b`, vitest, `npm run build` | Nativo con `actions/setup-node`, igual de rápido que `backend-lint` |
| `docs` | `docker compose run --rm docs build --strict` | **Con Docker Compose**: la imagen de MkDocs Material fijada a la 9 vive ahí, no como dependencia adicional del runner |

`.env.test.example` (nuevo en F6, versionado) es la plantilla de `.env.test`, paralela a `.env.example`. El job `backend-tests` la copia con `cp .env.test.example .env.test` antes de levantar `compose.test.yml`; sin ella, un clon nuevo del repositorio (incluido el runner de CI) no podía ejecutar los tests del backend sin crear el fichero a mano.

## 8. Ampliación de la v2

> Estado: **diseño, en construcción** · Fases F9–F17 · Depende de la [arquitectura de la v2](v2.md). Las desviaciones respecto a lo que ya existe van marcadas **[nuevo]**, y lo ya construido, **[construido]**. Hasta ahora: en F9, `mailpit`, `valkey`, `valkey-test`, `worker`, el volumen `files_data`, `infra/email/`, `infra/queue/`, `infra/storage/`, `infra/pdf/`, `worker.py` y `jobs/`; en F10, `manual` y su job de CI.

### 8.1 Servicios

| Servicio | Imagen u origen | Puerto en el host | Para qué | Fase |
|---|---|---|---|---|
| `valkey` **[construido]** | `valkey/valkey:9.1-alpine` | — | Cola de SAQ y contadores de rate limit (A18, A28) | F9 |
| `worker` **[construido]** | `./backend`, la **misma imagen** que `api` | — | Trabajos (PDF, IA, emails) y barridos programados | F9 |
| `mailpit` **[construido]** | `axllent/mailpit:v1.31` | 8025 (interfaz web) | Captura todos los emails en desarrollo; SMTP interno en el 1025 | F9 |
| `manual` **[construido]** | `./manual/Dockerfile.dev` (node 24) | 3001 | Documentación de producción (Docusaurus) con recarga en vivo (`--poll`, como el frontend). Sirve **un solo idioma**: el inglés se arranca con `--locale en` (ver `manual/README.md`) | F10 |
| `valkey-test` **[construido]** | como `valkey`, en `tmpfs` | — | Rate limit y cola en la suite de pytest | F9 |

Volumen nuevo: **`files_data`** **[construido]**, montado en `/data/files` en `api` **y** `worker` (A21). Es el almacén de los PDFs. La imagen crea `/data/files` con dueño `appuser` antes de montarlo ([ficheros §3](ficheros.md#3-escribir-y-leer-en-disco)).

Aclaraciones:

- **`worker` es `api` con otro comando.** Comparte imagen, volúmenes (código, `.venv`, `files_data`) y `env_file`. Así un trabajo usa exactamente los mismos services, modelos y dependencias que un endpoint, y no hay una segunda imagen que mantener. Depende de `db`, `valkey` y `supertokens` (los barridos de notificaciones piden el email del usuario a SuperTokens, A12).
- **Valkey no publica puerto**, igual que el core de SuperTokens. Guarda la cola en disco (`--appendonly yes` sobre el volumen `valkey_data`) para que reiniciar el contenedor no pierda los trabajos encolados; aun así, si se pierden, el barrido de la [arquitectura §3](v2.md#3-consistencia-entre-almacenes) los reencola.
- **`mailpit` es solo de desarrollo.** En producción no hay servicio de correo: el SMTP lo configura quien despliega (RNF-34), y sin configurar la aplicación arranca igual. `python -m app.scripts.send_test_email <dirección>` envía un email de prueba con la configuración vigente: en desarrollo llega a Mailpit, y al desplegar sirve para comprobar el SMTP sin esperar a que la aplicación necesite enviar algo.
- **No hay servicio de ficheros**: es un volumen (A21). La copia de seguridad de una instalación pasa a ser `pg_dump` de las dos bases de datos **más** una copia de `files_data`.

Fragmento de `compose.yml` (se conservan las convenciones de la v1: healthchecks, `depends_on` con `service_healthy`, volúmenes con nombre y versiones fijadas):

```yaml
  valkey:
    image: valkey/valkey:9.1-alpine
    command: ["valkey-server", "--appendonly", "yes"]
    volumes:
      - valkey_data:/data
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  worker:
    build:
      context: ./backend
    command: watchfiles --filter python "saq --quiet app.worker.settings" app
    volumes:
      - ./backend:/app
      - api_venv:/app/.venv
      - files_data:/data/files
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      valkey:
        condition: service_healthy
      supertokens:
        condition: service_healthy

  mailpit:
    image: axllent/mailpit:v1.31
    ports:
      - "8025:8025"

  api:
    volumes:
      - files_data:/data/files      # además de los volúmenes que ya tiene
    depends_on:
      valkey:
        condition: service_healthy
```

> **Trampa — el `worker` no recarga el código.** `api` arranca con `--reload`; el `worker` no, porque SAQ no lo trae. En desarrollo el comando va envuelto en `watchfiles` (viene con `uvicorn[standard]`), que reinicia el proceso al cambiar cualquier `.py` de `app/`. Al reiniciarse, SAQ avisa de que algunas tareas no terminaron dentro del periodo de gracia: son sus bucles internos (latido, barrido de trabajos abandonados), no trabajos del usuario. En producción (F7) el comando es `saq --quiet app.worker.settings`, sin `watchfiles`.

> **Trampa — SAQ configura el logging a su manera.** Sin `--quiet`, el CLI de SAQ llama a `logging.basicConfig(level=WARNING)` **antes** de importar `app.worker`; después, el `basicConfig` de la aplicación ya no hace nada y no sale ni el arranque del worker ni cada trabajo procesado. Con `--quiet` SAQ no toca el logging, y `app.worker` lo configura al importarse igual que `main.py`.

> **Trampa — las migraciones las aplica solo `api`.** El `entrypoint.sh` que aplica `alembic upgrade head` se queda en `api`. Si el `worker` arrancara también con él, dos procesos migrarían a la vez. El `worker` no usa ese entrypoint: si arranca antes de que termine la migración, sus primeros trabajos fallan y se reintentan.

### 8.2 Estructura del repositorio

```
applications-tracker/
├── compose.yml                 + valkey, worker, mailpit, manual; volúmenes files_data y valkey_data
├── compose.test.yml            + valkey-test
├── docs/                       MkDocs: documentación de DESARROLLO (sin cambios de estructura)
├── manual/                     [nuevo] Docusaurus: documentación de PRODUCCIÓN (F10)
├── backend/
├── frontend/
└── .claude/agents/             el documentador pasa a mantener docs/ y manual/ (F10)
```

### 8.3 Backend

```
backend/app/
├── worker.py                   [construido] configuración de SAQ: cola, funciones y tareas programadas. Solo cablea.
├── jobs/                       [construido] funciones de trabajo: abren sesión, construyen el service y lo llaman
│   ├── context.py              [construido] WorkerContext: el contexto de SAQ con las dependencias que crea worker.py
│   ├── documents.py            generar PDF (F13, F14)
│   ├── ai.py                   propuesta de CV o carta (F15)
│   ├── notifications.py        barridos de avisos y envío (F12)
│   └── maintenance.py          ficheros huérfanos, reencolar pendientes atascados, reclamos sin resultado
├── infra/                      [nuevo] adaptadores a sistemas externos, cada uno detrás de una interfaz
│   ├── queue/                  [construido] JobQueue · SaqJobQueue · InMemoryJobQueue (pruebas) · QueueUnavailableError
│   ├── storage/                [construido] FileStorage · LocalFileStorage (iter_keys llega en F13)
│   ├── email/                  [construido] EmailSender · SmtpEmailSender · DisabledEmailSender · RecordingEmailSender (pruebas)
│   ├── llm/                    LLMProvider · adapters/<proveedor>.py · FakeLLMProvider (pruebas)
│   │   └── prompts/            prompts versionados (A33): cv_tailoring/v1.md, cover_letter/v1.md
│   ├── pdf/                    [construido] PdfRenderer · WeasyPrintRenderer (weasyprint_renderer.py, que solo importa
│   │                           el worker: la API no carga WeasyPrint) · TemplateOnlyFetcher contra SSRF
│   ├── crypto.py               Fernet/MultiFernet para las claves de IA de los usuarios (A34)
│   └── rate_limit.py           `limits` sobre Valkey
├── templates/                  [nuevo]
│   ├── cv/<diseño>/            template.html, style.css, manifest.json y fuentes (A25)
│   ├── cover_letter/<diseño>/
│   └── email/<tipo>/           <idioma>.html y <idioma>.txt (A36)
├── domain/                     + notifications.py (tipos y claves de deduplicación), limits.py (LimitKey),
│                                 profile.py (enumerados del perfil), ai.py (esquema de la propuesta)
├── repositories/               + document, profile, ai_proposal, ai_provider_key, ai_consent,
│                                 notification_delivery, calendar_feed, user_limit_override
├── services/                   + document_service, profile_service, cv_generation_service,
│                                 ai_proposal_service, ai_key_service, notification_service,
│                                 limit_service, calendar_service
│   └── notifications/          + email.py: EmailChannel (segunda implementación de NotificationChannel)
├── api/v1/
│   ├── router.py               + router `public` con la lista blanca (calendario, baja de avisos)
│   ├── deps.py                 + fábricas de infra, require_verified_email, rate_limit(...)
│   └── endpoints/              + documents, profile, ai, usage, calendar, notifications
└── scripts/                    + set_user_limit.py (RF-143)
```

#### Reglas de capas (ampliación)

| Capa | Puede | No puede |
|---|---|---|
| `infra/` | Hablar con **un** sistema externo (disco, Valkey, SMTP, proveedor de IA, WeasyPrint) y traducir sus errores a excepciones propias | Conocer modelos SQLAlchemy o la BD · decidir reglas de negocio · importar `services/` |
| `jobs/` | Abrir una sesión de BD, construir el service con sus dependencias de `infra/` y llamar a **un** método del service | Contener reglas de negocio · ejecutar SQL · hacer `commit` (lo hace el service, invariante 6) |
| `worker.py` | Registrar funciones de `jobs/` y tareas programadas | Cualquier lógica |
| `services/` | Todo lo de la v1 **y** usar interfaces de `infra/` recibidas en el constructor, y **encolar después del commit** (invariante 11) | Importar implementaciones concretas de `infra/` (`SmtpEmailSender`, un adaptador de IA): solo sus interfaces |
| `templates/` | Presentación con Jinja2: formato de fechas, bucles, condicionales de maquetación | Lógica que decida qué contenido va (eso lo decide el service al preparar los datos) |
| `endpoints/` | Todo lo de la v1 y declarar `rate_limit(...)` y `require_verified_email` como dependencias | Usar `infra/` directamente |

**La regla que lo resume, ampliada:** *si algo habla con la base de datos o con SuperTokens, vive en `repositories/`; si habla con cualquier otro sistema externo, vive en `infra/` detrás de una interfaz; si algo decide, vive en `services/` o `domain/`.*

Dirección de dependencias: `endpoints / jobs → services → repositories + interfaces de infra`. Las implementaciones de `infra/` solo se eligen en `deps.py` (para la API) y en `worker.py` (para el worker), según la configuración. En las pruebas se pasan las implementaciones de prueba (`InMemoryJobQueue`, `RecordingEmailSender`, `FakeLLMProvider`).

### 8.4 Frontend

```
frontend/src/features/
├── documents/          [nuevo] biblioteca, subida, visor PDF (iframe sobre un blob: sin pdf.js)
├── profile/            [nuevo] editor del perfil por secciones, con orden por arrastre
├── cv-generation/      [nuevo] elegir diseño y secciones; estado pendiente → listo
├── ai/                 [nuevo] propuesta, revisión lado a lado (RF-118), carencias, claves y consentimiento
├── board/              [nuevo] tablero Kanban (dnd-kit)
├── calendar/           [nuevo] vista mensual y semanal propia (date-fns), suscripción ICS
├── usage/              [nuevo] página de uso y el aviso de consumo que se muestra donde se gasta (RF-144)
└── auth/               + recuperar contraseña, verificación de email, preferencias de notificación y zona horaria
```

| Tema | Convención |
|---|---|
| Recursos pendientes | **[nuevo]** Una query cuyo recurso está `pending`, `queued` o `running` usa `refetchInterval` hasta que cambia de estado. Una única utilidad decide el intervalo a partir del estado, para que ninguna pantalla se quede consultando indefinidamente. |
| Funciones con coste | **[nuevo]** El código `email_not_verified` (y los de cuota y rate limit) se traduce con el mismo `errorMessageKey`, y un componente común explica qué hacer (verificar, esperar, añadir una clave) en lugar de un aviso genérico. |
| Calendario | **[nuevo]** Rejilla propia con `date-fns`: hay pocos eventos y ya se tiene `date-fns`. Una librería de calendario completa (FullCalendar, react-big-calendar) pesaría más que la propia vista. |
| Arrastrar y soltar | **[nuevo]** `@dnd-kit` en el tablero y en el orden de los elementos del perfil: soporta teclado y pantallas táctiles (RF-123). |
| Visor de PDF | **[nuevo]** `apiClient.getBlob()` (ya existe para el CSV) más `URL.createObjectURL` en un `iframe`, que se libera al desmontar. |

Las reglas de capas del frontend no cambian: `services/` sigue siendo la única capa que usa `apiClient`.

### 8.5 Documentación de producción (`manual/`) [construido en F10]

```
manual/
├── package.json, docusaurus.config.ts, sidebars.ts   Docusaurus 3.10 y docusaurus-plugin-openapi-docs 5.2, fijados
├── Dockerfile.dev
├── scripts/                    prepare-openapi.mjs (copia derivada del contrato) y check-i18n.mjs
├── docs/                       español, idioma por defecto
│   ├── uso/                    manual de uso por tareas (RNF-33)
│   ├── despliegue/             visión general, requisitos, variables, correo y copias de seguridad; la receta de
│   │                           producción (compose, proxy, HTTPS) llega con F7
│   └── api/
│       ├── guia.md             integración: Bearer, errores, paginación, fechas, límites y CORS (rate limit: F11)
│       └── referencia/         GENERADA desde ../docs/referencia/openapi.json (no se versiona)
├── i18n/en/                    traducción al inglés de uso/, despliegue/ y api/guia.md, y los textos de navegación
└── i18n/es/code.json           textos del tema de OpenAPI en español (write-translations no los extrae)
```

- La referencia de la API la genera `docusaurus-plugin-openapi-docs` a partir del **mismo** `openapi.json` que ya versiona el backend. Se regenera en cada `start` y `build` y no se versiona la salida: una sola fuente del contrato. Antes de generarla, `prepare-openapi.mjs` deriva una copia con un servidor `{apiUrl}` editable (por defecto `http://localhost:8000`): sin él, los ejemplos apuntaban al origen del manual. El panel para enviar peticiones está oculto (CORS y sesiones mezcladas); para probar, Swagger en la API. Los ejemplos de código empiezan por curl.
- La referencia generada sale en el idioma de los docstrings del backend (español) también en la versión inglesa del sitio. Traducirla exigiría dos contratos OpenAPI: no se hace, y la guía de integración en inglés lo explica.
- En producción (F7), el manual se construye como estático y lo sirve el mismo Nginx que el frontend (por ejemplo, en `/manual`).

### 8.6 Variables de entorno nuevas

Van a `.env.example` y `.env.test.example`, y al manual de despliegue. Ninguna tiene un valor real versionado (RNF-03).

| Variable | Para qué | Si falta |
|---|---|---|
| `VALKEY_URL` **[construido]** | Cola (SAQ) y rate limit | No arranca: es infraestructura obligatoria |
| `FILES_ROOT` **[construido]** | Raíz del almacén de ficheros (`/data/files`) | No arranca |
| `PUBLIC_APP_URL` | Enlaces en los emails y en el feed ICS | No arranca |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY` (`none`, `starttls`, `tls`), `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, `SMTP_TIMEOUT_SECONDS` (30 por defecto) **[construido]** | Servidor de correo (RNF-34). Con `SMTP_HOST`, `EMAIL_FROM` es obligatorio: si falta, no arranca | Arranca **sin email**: las funciones dependientes aparecen como no disponibles |
| `APP_SECRET` | Firma de los enlaces de baja de avisos | No arranca |
| `AI_KEYS_ENCRYPTION_KEYS` | Claves maestras de Fernet, separadas por comas; la primera cifra y todas descifran (rotación, A34) | Las claves propias de IA quedan desactivadas |
| `AI_ENABLED_PROVIDERS` | Proveedores que se ofrecen a los usuarios (RF-151) | Ninguno: no se pueden añadir claves propias |
| `AI_MODEL_<PROVIDER>` | Modelo que usa cada proveedor habilitado | Ese proveedor no se habilita |
| `AI_PLATFORM_PROVIDER`, `AI_PLATFORM_API_KEY` | Clave de la plataforma para la cuota gratuita | Sin cuota gratuita: solo claves propias |
| `AI_FREE_USES`, `AI_MONTHLY_SPEND_CAP` | Cuota gratuita por cuenta y tope de gasto global (RF-150, RF-155) | Valores por defecto de la configuración |
| `TRUSTED_PROXIES` | IPs de los proxies cuyo `X-Forwarded-For` se acepta | Ninguna: se usa la IP de la conexión |
| `LIMIT_*` | Valores globales de los límites por usuario (RF-140) | Los de §10 de la especificación |

### 8.7 Convenciones nuevas del backend

| Tema | Convención |
|---|---|
| Trabajos | **[nuevo]** Cada trabajo recibe solo ids (`document_id`, `user_id`), carga la fila filtrando por los dos y **termina sin hacer nada** si ya no está pendiente. Así encolar dos veces, o reencolar desde un barrido, es inocuo. |
| Encolar | **[nuevo]** Solo después del `commit` (invariante 11), con un método del service que confirma y luego encola; nunca dentro de la transacción. |
| Tareas programadas | **[nuevo]** Las funciones de barrido reciben "ahora" como parámetro: el `worker` pasa el reloj real y las pruebas, una fecha fija. |
| Endpoints públicos | **[nuevo]** Se registran en el router `public`; la prueba T1 compara la lista de rutas sin sesión con una lista blanca escrita en el propio test. |
| Plantillas | **[nuevo]** Los CVs llevan sus fuentes dentro de la carpeta del diseño (`@font-face` con ficheros locales): el PDF sale igual en cualquier máquina y no depende de las fuentes instaladas en la imagen. |
| Prompts | **[nuevo]** Un fichero por versión (`v1.md`, `v2.md`); cambiar un prompt es añadir una versión nueva, no editar la anterior, para que las propuestas guardadas sigan explicándose (A33). |
| Pruebas | **[nuevo]** Ninguna prueba automática habla con un proveedor de IA ni con un SMTP real. Las implementaciones de prueba de `infra/` son parte del código, no mocks improvisados en cada test. |
| Códigos de error nuevos | `email_not_verified`, `email_unavailable`, `rate_limited`, `storage_limit_reached`, `invalid_file_type`, `file_too_large`, `document_in_use`, `profile_incomplete`, `job_description_missing`, `ai_consent_required`, `ai_free_quota_exhausted`, `ai_global_cap_reached`, `ai_provider_auth`, `ai_provider_quota`, `ai_provider_unavailable`, `ai_proposal_invalid`, además del patrón existente `<recurso>_limit_reached` |

Dependencias nuevas previstas (versiones fijadas al añadirlas, siempre con `docker compose exec api uv add`):

- **Backend:** `saq`, `limits[redis]`, `weasyprint`, `jinja2`, `aiosmtplib`, `cryptography`, `icalendar`, `pypdf` (comprobar que un PDF subido se abre, sin renderizarlo), `python-multipart` (subidas) y el SDK de cada proveedor de IA habilitado.
- **Imagen del backend:** las librerías de sistema de WeasyPrint (Pango, HarfBuzz) **[construido en F9]**; `fonts-dejavu-core` llega con ellas ([ficheros §7](ficheros.md#fuentes)).

Ya añadidas en F9: `saq[redis]`, `weasyprint`, `jinja2` y `aiosmtplib`. WeasyPrint no publica tipos (`py.typed`): sus imports llevan `# type: ignore[import-untyped]`, confinados a `weasyprint_renderer.py` y su prueba.
- **Frontend:** `@dnd-kit/core` y `@dnd-kit/sortable`.
- **Manual:** Docusaurus y `docusaurus-plugin-openapi-docs`, con versiones fijadas (mismo criterio que MkDocs, R4).

### 8.8 Integración continua

| Job | Cambio |
|---|---|
| `backend-tests` | `compose.test.yml` añade `valkey-test`; los ficheros van a un directorio temporal por prueba |
| `manual` **[construido]** | Nativo con Node 24: `npm ci`, `npm run check-i18n` (cada página en los dos idiomas), `npm run build` (falla ante enlaces rotos, igual que `mkdocs build --strict`) y `npm run typecheck` después del build, porque `sidebars.ts` importa la referencia generada |
| `docs` | Sin cambios |

### 8.9 Decisiones cerradas de la v2

Confirmadas con el usuario durante el diseño (2026-09-24), a continuación de las de la v1:

| # | Decisión | Regla derivada |
|---|---|---|
| 12 | Registro abierto | Límites, rate limiting y verificación son defensas reales |
| 13 | Verificación exigida solo para lo que tiene coste | `require_verified_email` en IA, ficheros y emails; el resto de la app funciona sin verificar |
| 14 | Biblioteca de documentos reutilizable | La solicitud referencia documentos; un documento en uso no se borra, se archiva |
| 15 | IA: ajuste guiado en un paso, con revisión | Sin chat; la propuesta se valida y se revisa antes de generar |
| 16 | IA: cuota gratuita fija sin renovación y después clave propia de un proveedor habilitado | Nunca se pasa en silencio a la clave de la plataforma |
| 17 | Cuatro tipos de email, cada uno desactivable | Reclamar antes de enviar; nunca dos veces |
| 18 | SMTP configurado por quien despliega, con variables de entorno | Sin SMTP, la aplicación arranca y lo que depende del email aparece como no disponible |
| 19 | Documentación de producción en Docusaurus, es + en, con despliegue, uso y API | Referencia de la API generada del mismo OpenAPI; el documentador mantiene los dos sitios |
| 20 | Límites con consumo y restante visibles | También donde se gasta, con aviso al 80 % |
| 21 | Ficheros en disco local | Volumen compartido por `api` y `worker`; S3 como implementación futura de `FileStorage` |
| 22 | Valkey para la cola y el rate limit | SAQ sobre Valkey; la cola podría pasar a Postgres cambiando la URL |
