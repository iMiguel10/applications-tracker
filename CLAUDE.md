# CLAUDE.md

Guía de trabajo para Claude Code (y cualquier colaborador) en **Applications Tracker**.

## 1. Qué es

Aplicación para registrar y seguir solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y los recordatorios del próximo paso. Es un proyecto de portfolio que además se usa de verdad.

> **Estado (2026-09-22):** diseño cerrado, sin código de producto todavía.
>
> - **Existe:** el entorno Docker de desarrollo, un endpoint `/api/v1/health` con su página de prueba y la documentación en `docs/`.
> - **No existe todavía:** autenticación (SuperTokens), modelos, migraciones, repositories, services de negocio ni features del frontend.
>
> Todo lo que este documento describe sobre esas piezas es la **norma a seguir** al construirlas, no algo que se pueda consultar ya en el código.

## 2. Documentación

Sitio MkDocs en `docs/` (servido en http://localhost:8001). Es la fuente de verdad del diseño. Este fichero la resume sin duplicarla.

| Documento | Para qué |
|---|---|
| `docs/producto/especificacion.md` | Requisitos (RF-xx, RNF-xx), ciclo de vida y **reglas de transición**, límites, fases |
| `docs/arquitectura/index.md` | Decisiones A1–A17 con alternativas descartadas, modelo de datos, flujos, invariantes |
| `docs/arquitectura/servicios-y-estructura.md` | Servicios de compose, estructura, **reglas de capas**, convenciones heredadas |
| `docs/arquitectura/autenticacion.md` | SuperTokens: integración, trampas, pruebas adversas |
| `docs/decisiones/` | Bitácora de cambios de rumbo durante el desarrollo, con plantilla |

**Si el código y un documento no coinciden, no se corrige el documento sin más.** Primero se averigua si el diseño evolucionó (y se actualiza el documento dejando constancia) o si la implementación se lo saltó (y entonces es un fallo del código).

## 3. Stack y servicios

| Servicio | Puerto | Notas |
|---|---|---|
| `db` | 5432 | Postgres 17, datos de la app, gestionados por Alembic |
| `api` | 8000 | FastAPI + SQLAlchemy async + Alembic (python 3.12, uv). `/docs` = OpenAPI. |
| `frontend` | 5173 | React 19 + TS + Vite 8, TanStack Query, react-hook-form + zod, Tailwind v4 + shadcn/ui, i18next |
| `docs` | 8001 | MkDocs Material **fijado a la 9** (MkDocs 2.0 rompe plugins y temas) |
| `supertokens`, `supertokens-db` | — | **F1, aún no existen.** Core de auth con **su propia** instancia de Postgres; no se publican puertos. |

Usa siempre `localhost` y nunca `127.0.0.1` (ver trampas).

## 4. Comandos

```bash
cp .env.example .env                  # primera vez
docker compose up --build             # todo el entorno de desarrollo
docker compose up --build -V          # tras cambiar dependencias (renueva los volúmenes anónimos)

# Backend
docker compose exec api ruff check .
docker compose exec api ruff format .
docker compose exec api mypy app
docker compose exec api alembic revision --autogenerate -m "descripcion"   # revisar SIEMPRE el fichero generado
docker compose exec api alembic upgrade head                               # también se aplica al arrancar api
docker compose exec api uv add <paquete>                                   # nunca uv/pip en el host

# Tests del backend (BD aislada)
docker compose -f compose.test.yml up --build --abort-on-container-exit --exit-code-from api-test
docker compose -f compose.test.yml down -v

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npx tsc -b
docker compose exec frontend npm run build
docker compose run --rm frontend npm install <paquete>
docker compose exec frontend npx shadcn@latest add <componente>            # nunca escribir componentes ui a mano

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
3. `applications.status` es igual al `to_status` del último cambio del historial, ordenado por **`created_at`** (no por `changed_at`).
4. El estado solo cambia vía `ApplicationStatusService`, con `SELECT … FOR UPDATE`. `PATCH /applications/{id}` no acepta `status`.
5. Toda solicitud tiene al menos un cambio en su historial (el inicial).
6. Las transacciones las confirma el service; un repository nunca hace `commit`.
7. Las reglas de transición y la política de contraseñas viven **solo en el backend**. El frontend usa `allowed_transitions` y los `FIELD_ERROR` de SuperTokens.
8. Todo endpoint protegido depende de `get_current_user`; ninguno usa `verify_session()` directamente.
9. `users` no copia datos de identidad (ni email ni nombre): se piden a SuperTokens.
10. Solo el SDK de SuperTokens refresca la sesión; `apiClient` no gestiona el 401.

## 8. Trampas conocidas

- **Dependencias que "no se instalan".** `api_venv` (volumen con nombre) y `/app/node_modules` (volumen anónimo) **no se actualizan al reconstruir la imagen**. Instala dentro del contenedor. Tras un `git pull` con dependencias nuevas: `docker compose up --build -V` y `docker compose run --rm api uv sync`.
- **Orden de middlewares.** SuperTokens se añade **antes** que `CORSMiddleware` (en Starlette el último añadido es el más externo). Si se invierte, el login devuelve 200 y aun así el navegador bloquea la respuesta con un error de CORS.
- **`localhost` frente a `127.0.0.1`.** Para el navegador son sitios distintos: las cookies de sesión no viajan y el login parece no funcionar sin dar error.
- **Caché tras el logout.** `signOut()` y la sesión expirada ejecutan `queryClient.clear()` antes de navegar; si no, el siguiente usuario ve datos del anterior.
- **Deshacer un cambio de estado** ordena por `created_at`. Ordenar por `changed_at` (fecha que declara el usuario) borraría el cambio equivocado.
- **Alembic autogenerate** no detecta cambios en `CHECK` ni en índices funcionales como `lower(name)`: revisa y completa cada migración a mano.
- **Finales de línea:** `entrypoint.sh` debe tener LF (lo fuerza `.gitattributes`). Con CRLF, el contenedor `api` no arranca.

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
| **F0** | Esqueleto vertical **desechable**: crear y listar solicitudes sin auth, atravesando todas las capas |
| F1 | SuperTokens (core + BD), `users`, `get_current_user`, login y registro, rutas protegidas |
| F2 | Empresas y solicitudes: CRUD, filtros, paginación, archivado, pruebas de aislamiento, OpenAPI en docs |
| F3 | Ciclo de vida: historial, transiciones, deshacer, `allowed_transitions` |
| F4 | Entrevistas y recordatorios (`in_app` + `NotificationChannel`) |
| F5 | Dashboard y exportación CSV |
| F6 | CI con GitHub Actions |
| F7 | Preparación para despliegue |
