# Servicios y estructura

> Estado: **borrador v1** · Fecha: 2026-09-22 · Depende de la [arquitectura](index.md)
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
| `supertokens-db` | `postgres:17` | — | Base de datos exclusiva del core de SuperTokens | F1 |
| `supertokens` | `registry.supertokens.io/supertokens/supertokens-postgresql` | — | Core de autenticación: usuarios, contraseñas, sesiones | F1 |
| `mailpit` | `axllent/mailpit` | 8025 (UI) | Captura los emails en desarrollo | `[C]` Llega con la recuperación de contraseña o el canal de email |
| `api-test`, `db-test` | como `api` y `db` | — | Suite de pytest contra una BD aislada (`compose.test.yml`) | ✔ existe |

Aclaraciones:

- **`db` y `supertokens-db` son dos instancias con la misma imagen** (decisión A11). Así Alembic nunca ve las tablas de SuperTokens y cada BD se puede respaldar o resetear por separado.
- **El core de SuperTokens no publica puerto.** Solo `api` habla con él por la red interna de Docker (`http://supertokens:3567`). El navegador nunca lo ve.
- **`mailpit` está considerado pero no se añade** hasta que algo envíe emails. Meterlo antes es un servicio que arranca sin usarse.

Esqueleto de lo que se añade a `compose.yml` en F1. Se conservan los detalles heredados: healthchecks, `depends_on` con `service_healthy` y volúmenes con nombre.

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
    image: registry.supertokens.io/supertokens/supertokens-postgresql
    environment:
      POSTGRESQL_CONNECTION_URI: postgresql://${SUPERTOKENS_DB_USER}:${SUPERTOKENS_DB_PASSWORD}@supertokens-db:5432/${SUPERTOKENS_DB_NAME}
      API_KEYS: ${SUPERTOKENS_API_KEY}
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
> - **Solución.** Instalar siempre las dependencias **dentro** del contenedor (`docker compose exec api uv add …`, `docker compose run --rm frontend npm install …`). Después de un `git pull` que cambie dependencias, usar `docker compose up --build -V`: `-V` renueva los volúmenes anónimos, y además `docker compose run --rm api uv sync` para el volumen con nombre.

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
│   ├── repositories/           [nuevo] todo el acceso a la BD
│   │   └── application_repository.py
│   ├── services/               reglas de negocio y transacciones
│   │   ├── application_service.py
│   │   ├── application_status_service.py
│   │   └── notifications/      NotificationChannel + InAppChannel (F4)
│   └── api/v1/
│       ├── router.py           agrega los routers
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

> **Fallos encontrados en la plantilla**, anotados de paso; ya se corrigieron en este proyecto al copiarla:
>
> - `main.py` pasaba `settings.cors_origins` (un `str`) a `allow_origins` en lugar de `cors_origins_list`.
> - El `.dockerignore` estaba en la raíz, pero el contexto de build es `./backend`, así que no se aplicaba.
> - `/app` y `.venv` pertenecían a root, lo que impedía a `appuser` escribir la caché de pytest o ejecutar `uv add`.
> - mypy daba 3 errores (faltaba el plugin de pydantic, y el handler tenía una firma incompatible con Starlette).

## 4. Frontend

```
frontend/src/
├── main.tsx, App.tsx          providers (QueryClient, SuperTokens en F1) + RouterProvider + Toaster
├── app/providers/             AuthProvider: estado de sesión y useAuth() (F1)
├── features/
│   ├── auth/                  login, registro, logout (F1)
│   ├── companies/             (F2)
│   ├── applications/          solicitudes + cambios de estado (F2, F3)
│   ├── interviews/            (F4)
│   ├── reminders/             (F4)
│   ├── dashboard/             (F5)
│   └── health/                página temporal de la Fase 1; se retira cuando exista el dashboard
├── pages/                     una página por ruta
├── routes/                    Router.tsx + AuthLoaders.ts
├── shared/
│   ├── components/{ui,form,common,layout}
│   ├── config/navigation.ts
│   ├── hooks/                 useDebounce, useUrlFilters…
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
| Filtros de listados | Estado local | Parámetros de la URL (`useUrlFilters`), decisión A16 |
| Módulo genérico `tracking` | Factory para 5 módulos idénticos | No aplica: no hay entidades con la misma forma |
| Tipos | Escritos a mano en `types/` | Igual: a mano. Ver la decisión cerrada 9. |
| Utilidad `cn` | `clsx` + `tailwind-merge` en `shared/lib/utils.ts` | **[nuevo]** shadcn 4.2x genera los componentes con `import { cn } from "cn"`, el paquete oficial `shadcn-ui/cn`. `shared/lib/utils.ts` lo reexporta para que el código propio siga importando de `@/shared/lib/utils`; `clsx` y `tailwind-merge` se eliminan. |
| ESLint en `ui/` | Sin excepción: `npm run lint` fallaba por `buttonVariants` | **[nuevo]** `react-refresh/only-export-components` desactivada solo en `src/shared/components/ui/**`, que es código generado y no se edita |
| Tipo `Page<T>` | No existía | **[nuevo]** `shared/types/Page.ts`, espejo de `schemas/pagination.py` |

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
| 6 | Se mantiene `changed_at` en el historial | Deshacer ordena por `created_at`; las métricas usan `changed_at` |
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
