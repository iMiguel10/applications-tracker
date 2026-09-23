# CLAUDE.md

Guía de trabajo para Claude Code (y cualquier colaborador) en **Applications Tracker**.

## 1. Qué es

Aplicación para registrar y seguir solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y los recordatorios del próximo paso. Es un proyecto de portfolio que además se usa de verdad.

> **Estado (2026-09-23): F4, F5 y F6 terminadas.**
>
> F6 (CI) se construyó antes que F5 (dashboard y exportación CSV) por decisión explícita del usuario, no porque F5 no hiciera falta; ver [0006](docs/decisiones/0006-ci-antes-que-f5.md). Con F5 cerrada, sigue pendiente F7 (preparación para despliegue).
>
> - **Existe:**
>     - Entorno Docker, autenticación (F1) y documentación OpenAPI con referencia versionada.
>     - F2: empresas y solicitudes completas, con CRUD, filtros, búsqueda, orden y paginación en la URL, archivado, cuotas y aislamiento entre usuarios (T2, T3), tanto en backend como en frontend.
>     - F3: ciclo de vida completo. `domain/application_status.py` con la tabla `ALLOWED_TRANSITIONS`; `application_status_changes` (historial append-only, `seq` como orden real); `ApplicationStatusService` (cambiar y deshacer, con `SELECT … FOR UPDATE`); `allowed_transitions` en `ApplicationRead`; en el frontend, el diálogo de cambio de estado, la línea de tiempo del historial y deshacer.
>     - F4: entrevistas y recordatorios. `interviews` (CRUD completo, hija de `applications`, sin `user_id` propio); `reminders` (raíz con `user_id`, FK compuesta opcional a `applications`, cuota de 500 **pendientes**); `services/notifications/` con `NotificationChannel` e `InAppChannel` (no-op, costura de RF-53); solo crear/listar/completar/descartar para recordatorios, sin editar ni borrar (ninguna RF de recordatorios lo pide). En el frontend, ambas secciones viven embebidas en el detalle de la solicitud, y la sugerencia de RF-42 (proponer `interviewing` al programar una entrevista) usa `allowed_transitions`. **Los recordatorios no tienen página ni ruta propias en F4** (decisión [0005](docs/decisiones/0005-recordatorios-sin-pagina-global-en-f4.md)): se crean y ven filtrados por solicitud; la API ya admite un listado global y un recordatorio suelto (`application_id` nulo), pensando en F5.
>     - F5: dashboard y exportación CSV. `GET /dashboard` (`app/domain/dashboard.py`, `app/services/dashboard_service.py`, `app/schemas/dashboard.py`) agrega en una sola respuesta el recuento por estado (RF-60), los envíos por semana en las últimas 12 semanas (RF-61), la tasa de respuesta (RF-62, `null` con menos de 5 solicitudes enviadas por RF-66), las próximas entrevistas y los recordatorios pendientes o vencidos (RF-63) y las solicitudes sin actividad (RF-64); cada lista trae un vistazo de 5 elementos y su total. Las métricas de **estado actual** excluyen las solicitudes archivadas y las que retratan **lo ocurrido** las incluyen (detalle en `docs/arquitectura/index.md`). `GET /applications/export` (RF-70) vuelca a CSV todas las solicitudes del usuario, archivadas incluidas, con los códigos en crudo de los enumerados; registrado antes de `/{application_id}` en el router para que `export` no se lea como un UUID. En el frontend, `features/dashboard/` (seis widgets, `recharts` como dependencia nueva) y `pages/DashboardPage.tsx`, que sustituye a `/applications` como página de inicio (`/` redirige a `/dashboard`); `pages/RemindersPage.tsx` en `/reminders` cierra el hueco que dejó la decisión [0005](docs/decisiones/0005-recordatorios-sin-pagina-global-en-f4.md) (filtro por estado en la URL, paginación, crear/completar/descartar, mismo alcance que ya tenía la API); `ReminderFormDialog` ya no exige un `applicationId` fijo: si se omite, deja elegir la solicitud o dejar el recordatorio sin ligar (RF-50). Botón "Exportar CSV" en `ApplicationsPage` vía `apiClient.getBlob()` y `shared/lib/download.ts`.
>     - F6: integración continua. `.github/workflows/ci.yml`, 4 jobs en cada push/PR a `main`: `backend-lint` (ruff + mypy, nativo con `uv`, sin Docker), `backend-tests` (`compose.test.yml`, 238 tests), `frontend` (eslint, `tsc -b`, vitest, build) y `docs` (`mkdocs build --strict`). `.env.test.example` es la plantilla versionada de `.env.test`, antes inexistente.
> - **No existe todavía:** nada del alcance descrito en la especificación (F0–F6 están completas). Quedan F7 (preparación para despliegue) y F8 (revisión final).

## 2. Documentación

Sitio MkDocs en `docs/` (servido en http://localhost:8001). Es la fuente de verdad del diseño. Este fichero la resume sin duplicarla.

| Documento | Para qué |
|---|---|
| `docs/producto/especificacion.md` | Requisitos (RF-xx, RNF-xx), ciclo de vida y **reglas de transición**, límites, fases |
| `docs/arquitectura/index.md` | Decisiones A1–A17 con alternativas descartadas, modelo de datos, flujos, invariantes |
| `docs/arquitectura/servicios-y-estructura.md` | Servicios de compose, estructura, **reglas de capas**, convenciones heredadas |
| `docs/arquitectura/autenticacion.md` | SuperTokens: integración, trampas, pruebas adversas |
| `docs/guias/documentar-la-api.md` | Cómo se documenta un endpoint, cómo probar desde Swagger y cómo integrarse (Bearer) |
| `docs/referencia/openapi.json` | Copia **generada** del OpenAPI (no se edita a mano) que publica la referencia del sitio |
| `docs/decisiones/` | Bitácora de cambios de rumbo durante el desarrollo, con plantilla |

**Si el código y un documento no coinciden, no se corrige el documento sin más.** Primero se averigua si el diseño evolucionó (y se actualiza el documento dejando constancia) o si la implementación se lo saltó (y entonces es un fallo del código).

## 3. Stack y servicios

| Servicio | Puerto | Notas |
|---|---|---|
| `db` | 5432 | Postgres 17, datos de la app, gestionados por Alembic |
| `api` | 8000 | FastAPI + SQLAlchemy async + Alembic (python 3.12, uv). `/docs` = OpenAPI. |
| `frontend` | 5173 | React 19 + TS + Vite 8, TanStack Query, react-hook-form + zod, Tailwind v4 + shadcn/ui, i18next |
| `docs` | 8001 | MkDocs Material **fijado a la 9** (MkDocs 2.0 rompe plugins y temas) |
| `supertokens`, `supertokens-db` | — | Core de auth **fijado a 12.2.0** (debe implementar la CDI de `supertokens-python`), con **su propia** instancia de Postgres; no se publican puertos. Access token de 5 min ([0002](docs/decisiones/0002-access-token-de-5-minutos.md)). |

Usa siempre `localhost` y nunca `127.0.0.1` (ver trampas).

## 4. Comandos

```bash
cp .env.example .env                  # primera vez
docker compose up --build             # todo el entorno de desarrollo
docker compose up --build -V          # tras cambiar dependencias (renueva los volúmenes anónimos)

# Backend
docker compose exec api ruff check .
docker compose exec api ruff format .
docker compose exec api mypy app tests
docker compose exec api alembic revision --autogenerate -m "descripcion"   # revisar SIEMPRE el fichero generado
docker compose exec api alembic upgrade head                               # también se aplica al arrancar api
docker compose exec api uv add <paquete>                                   # nunca uv/pip en el host
docker compose exec api python -m app.scripts.export_openapi               # tras cambiar endpoints/schemas, mismo commit
docker compose -f compose.test.yml run --rm api-test python -m app.scripts.check_performance   # RNF-10/RNF-11 a mano, no en CI

# Tests del backend (BD aislada)
cp .env.test.example .env.test                                             # primera vez
docker compose -f compose.test.yml up --build --abort-on-container-exit --exit-code-from api-test
docker compose -f compose.test.yml down -v

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npx tsc -b
docker compose exec frontend npm run build
docker compose exec frontend npm run test                                  # vitest
docker compose exec frontend npm install <paquete>                         # exec, NO run (ver trampas)
docker compose exec frontend npx shadcn add <componente>                   # versión del proyecto; nunca escribir ui a mano

# Documentación
docker compose run --rm docs build --strict                                # falla ante enlaces rotos
```

## 5. Estructura y capas

**Backend:** `endpoints → services → repositories → models`. `domain/` (reglas puras) se usa desde `services` y `schemas`.

| Capa | Puede | No puede |
|---|---|---|
| `api/v1/endpoints/` | Validar con schemas, `Depends`, llamar a **un** service | Consultar la BD, reglas de negocio, `commit` |
| `services/` | Reglas de negocio, `domain/`, repositories, **`commit`/`rollback`**, lanzar `AppException` | Importar FastAPI, construir SQL |
| `repositories/` | Consultas SQLAlchemy, `add`/`flush`/`delete` | `commit`, reglas de negocio, métodos sin `user_id` sobre datos de usuario |
| `domain/` | Enums, tabla de transiciones, funciones puras | Cualquier I/O |

**Regla única:** *si habla con la BD, vive en `repositories/`; si decide, vive en `services/` o `domain/`.*

Patrón para un recurso nuevo en el backend: `domain/` (si tiene reglas) → `models/` → migración (revisada) → `repositories/` → `schemas/` → `services/` → `endpoints/` + `router.py` → pruebas de repository, service y API (incluida la de aislamiento) → documentación.

**Frontend (feature-based, heredado de `frontend_gestpro`):** `features/<f>/types` → `schemas` (zod, mensajes = claves i18n) → `services` (única capa que usa `apiClient`) → `<f>.keys.ts` → `hooks/queries` y `hooks/mutations` → `components` → `pages/` → `routes/Router.tsx` → `shared/config/navigation.ts` → claves en `es.json` **y** `en.json`.

## 6. Convenciones

- **Idioma:** identificadores en inglés; UI, comentarios, documentación y mensajes de commit en español.
- **Commits:** `tipo: descripción` (`feat`, `fix`, `docs`, `chore`, `test`, `refactor`). El código y su documentación van en el **mismo commit**.
- **Ids:** UUID (`gen_random_uuid()`). **Fechas:** `timestamptz` en UTC; `applied_at` es `date`.
- **Enumerados:** `varchar` + `CHECK` + `StrEnum`. Nunca enum nativo de Postgres.
- **Constraints:** con nombre determinista (`naming_convention` en `db/base.py`).
- **Errores:** `AppException` con `code` estable → `{"detail", "code"}`. El frontend traduce por `code` (`errors.<code>`).
- **Services y repositories:** clases que reciben la `AsyncSession`; `deps.py` las construye por petición.
- **Paginación:** `page` + `limit` (máx. 100) → `{items, total, page, limit, pages}`. Ordenación: `sort_by` + `order` contra una lista blanca.
- **Frontend:** alias `@/`; formularios con `shared/components/form/*`; filtros de listados en la URL; nunca `fetch` fuera de `apiClient`.
- **Calidad:** ruff, mypy, eslint y `tsc -b` sin errores antes de cada commit.

## 7. Invariantes que no se rompen

Violarlas es un fallo, no una diferencia de criterio.

1. Todo método de repository sobre datos de usuario recibe `user_id` y filtra por él.
2. Un recurso de otro usuario responde **404**, nunca 403.
3. `applications.status` es igual al `to_status` del cambio del historial con el **`seq` más alto** ([0004](docs/decisiones/0004-secuencia-para-ordenar-el-historial.md)). Nunca se ordena por fechas.
4. El estado solo cambia vía `ApplicationStatusService`, con `SELECT … FOR UPDATE`. `PATCH /applications/{id}` no acepta `status`.
5. Toda solicitud tiene al menos un cambio en su historial (el inicial).
6. Las transacciones las confirma el service; un repository nunca hace `commit`.
7. Las reglas de transición y la política de contraseñas viven **solo en el backend**. El frontend usa `allowed_transitions` y los `FIELD_ERROR` de SuperTokens.
8. Todo endpoint protegido depende de `get_current_user`; ninguno usa `verify_session()` directamente.
9. `users` no copia datos de identidad (ni email ni nombre): se piden a SuperTokens.
10. Solo el SDK de SuperTokens refresca la sesión; `apiClient` no gestiona el 401.

## 8. Trampas conocidas

- **Dependencias que "no se instalan".** `api_venv` (volumen con nombre) y `/app/node_modules` (volumen anónimo) **no se actualizan al reconstruir la imagen**. Instala dentro del contenedor **en marcha, con `exec`**. `docker compose run --rm frontend npm install` crea un contenedor nuevo con su propio `node_modules`: el paquete se pierde y el contenedor `frontend` nunca lo ve, aunque `package.json` sí cambie. Tras un `git pull` con dependencias nuevas: `docker compose up --build -V` y `docker compose run --rm api uv sync`.
- **Variables nuevas del `.env` no se aplican con `restart`.** `env_file` se lee al **crear** el contenedor: usa `docker compose up -d --force-recreate <servicio>`.
- **El logout no invalida al instante un access token ya emitido.** Se valida sin consultar al core, así que una copia sigue sirviendo hasta caducar (5 min). El refresh token sí queda revocado ([0002](docs/decisiones/0002-access-token-de-5-minutos.md)).
- **Endpoints nuevos: dentro del router `protected`** de `api/v1/router.py`, salvo que deban ser públicos. La prueba T1 lee las rutas del OpenAPI y falla si alguno responde sin sesión.
- **Endpoints documentados o los tests fallan.** Cada operación necesita `summary=` y un docstring (se publica como descripción para integradores). Y `docs/referencia/openapi.json` debe regenerarse con `export_openapi`: un test lo compara con la app.
- **Login sin `st-auth-mode` = tokens en cabeceras, no cookies** (decisión 0003). El frontend fija `tokenTransferMethod: "cookie"`; no lo quites.
- **El refresh token rota en cada uso.** Reutilizar uno ya usado se trata como robo y revoca la sesión: una integración debe guardar el par nuevo tras cada refresco.
- **`POST /auth/session/refresh → 401` al abrir el login sin sesión es normal**: `doesSessionExist()` pregunta así si hay sesión. Y `sFrontToken` es legible desde JS a propósito: no lleva firma y no sirve para autenticarse.
- **Orden de middlewares.** SuperTokens se añade **antes** que `CORSMiddleware` (en Starlette el último añadido es el más externo). Si se invierte, el login devuelve 200 y aun así el navegador bloquea la respuesta con un error de CORS.
- **`localhost` frente a `127.0.0.1`.** Para el navegador son sitios distintos: las cookies de sesión no viajan y el login parece no funcionar sin dar error.
- **Caché tras el logout.** `signOut()` y la sesión expirada ejecutan `queryClient.clear()` antes de navegar; si no, el siguiente usuario ve datos del anterior.
- **Deshacer un cambio de estado** ordena por `seq` (columna de identidad del historial). Por `changed_at` (fecha que declara el usuario) o por `created_at` (reloj del sistema, que puede retroceder) se borraría el cambio equivocado.
- **Alembic autogenerate** no incluye los `CHECK` al modificar una tabla existente (solo al crear una), y añade columnas `NOT NULL` sin default a tablas con filas, lo que hace fallar la migración. Revisa y completa cada migración a mano; comprueba con `alembic check` que modelos y BD coinciden, y aplica `downgrade -1` + `upgrade head` para probar que es reversible. Los valores de enums se congelan como texto dentro de la migración.
- **`comando | tail` oculta el código de salida real** (el que se ve es el de `tail`). Para saber si ESLint, `tsc` o pytest han fallado, ejecútalos sin tubería o redirige a un fichero.
- **Login en Swagger cierra la sesión de la app** en ese navegador: el login en modo cabecera caduca las cookies de sesión. Usa Swagger en una ventana privada.
- **Pydantic comprueba `pattern` antes que `to_upper`** en `StringConstraints`: normaliza con `BeforeValidator`.
- **Fechas sin hora en el frontend:** usa `shared/lib/dates.ts`, nunca `new Date("yyyy-MM-dd")` (medianoche UTC = el día anterior al oeste de UTC).
- **Base UI no es Radix:** los *triggers* usan `render={<Button />}`, no `asChild`.
- **Finales de línea:** `entrypoint.sh` debe tener LF (lo fuerza `.gitattributes`). Con CRLF, el contenedor `api` no arranca.
- **`now()` frente a `clock_timestamp()`.** `now()` es la hora de *inicio de la transacción*: todas las filas de una transacción empatan y el orden por `created_at` queda al azar. Esto pasa siempre en los tests, que corren en una transacción externa. `created_at` usa siempre `clock_timestamp()` ([decisión 0001](docs/decisiones/0001-clock-timestamp-en-created-at.md)).
- **Modelo nuevo invisible para Alembic.** Si no se importa en `app/models/__init__.py`, autogenerate no lo ve y genera un `drop_table`.
- **Tests y `commit`.** No abras sesiones propias en los tests: usa el fixture `db_session` (transacción externa + savepoints) o `client`, que sustituye `get_db` por esa sesión. Una sesión aparte confirmaría datos de verdad en `db-test`.
- **shadcn genera `import { cn } from "cn"`.** Es el paquete oficial `shadcn-ui/cn`; `@/shared/lib/utils` lo reexporta. No lo cambies a mano en los componentes generados.
- **`changed_at` exige zona horaria, pero el selector de fecha solo captura un día.** El schema (`AwareDatetime`) rechaza con 422 un datetime "naive", y `FormDatePicker` (heredado de F2) solo devuelve `"yyyy-MM-dd"`. Combinar ese día con medianoche local haría que elegir "hoy" cayera antes del último cambio ya registrado (que tiene la hora real de "ahora") y el backend lo rechazaría con 422 `changed_at_before_last_change`, de forma confusa para quien solo quería decir "ahora mismo". `applicationStatusChangeService.toChangedAt()` combina el día elegido con la **hora local actual**, no medianoche; probado en `applicationStatusChange.service.test.ts`.

## 9. Agentes

Están en `.claude/agents/`. Se invocan explícitamente al cerrar una feature o una fase; no corren solos.

| Agente | Cuándo |
|---|---|
| `docs-writer` | Al cerrar una feature, un endpoint o una migración, o si el código parece haber divergido del diseño |
| `qa-verifier` | Antes de dar por terminado un bloque de trabajo: tipos, estilo, tests (incluidos los adversos) y verificación en vivo |

## 10. Fases

| Fase | Contenido |
|---|---|
| ✔ Entorno | Docker de desarrollo, health, sitio de documentación |
| ✔ F0 | Esqueleto vertical desechable: crear y listar solicitudes sin auth, atravesando todas las capas |
| ✔ F1 | SuperTokens (core + BD), `users`, `get_current_user`, router protegido, login y registro, rutas protegidas |
| ✔ F2 | Empresas y solicitudes: CRUD, filtros, paginación, archivado, pruebas de aislamiento, OpenAPI en docs |
| ✔ F3 | Ciclo de vida: historial, transiciones, deshacer, `allowed_transitions` |
| ✔ F4 | Entrevistas y recordatorios (`in_app` + `NotificationChannel`) |
| ✔ F5 | Dashboard (`GET /dashboard`), exportación CSV (`GET /applications/export`) y página global de recordatorios (`/reminders`) |
| ✔ F6 | CI con GitHub Actions (construida antes que F5, a petición explícita del usuario; ver [0006](docs/decisiones/0006-ci-antes-que-f5.md)) |
| F7 | Preparación para despliegue |
| F8 | Revisión final: funcionalidades faltantes, mejoras pendientes y diseño de la UI |
