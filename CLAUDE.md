# CLAUDE.md

Guía de trabajo para Claude Code (y cualquier colaborador) en **Applications Tracker**.

## 1. Qué es

Aplicación para registrar y seguir solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y los recordatorios del próximo paso. Es un proyecto de portfolio que además se usa de verdad.

> **Estado (2026-09-30): MVP terminado (F0–F6 y F8). La v2 (F9–F17) está especificada y diseñada; construidas F9 (infraestructura: correo, cola con `worker`, almacén de ficheros y PDF), F10 (manual de producción en `manual/`), F11 (cuenta y abuso), F12 (avisos por email) y F13 (biblioteca de documentos). F7 (despliegue) espera a que haya un VPS.**
>
> F6 (CI) se construyó antes que F5 (dashboard y exportación CSV) por decisión explícita del usuario, no porque F5 no hiciera falta; ver [0006](docs/decisiones/0006-ci-antes-que-f5.md). F8 (revisión final) se construyó a su vez antes que F7 por otra decisión explícita del usuario: con el MVP funcional completo (F0–F6), tenía más sentido cerrar la revisión mientras el diseño estaba fresco que dejarla para después de desplegar. F7 cambia de contenido: ya no es "preparación para despliegue" sino la **puesta en producción real**, y sigue sin empezar.
>
> - **Existe:**
>     - Entorno Docker, autenticación (F1) y documentación OpenAPI con referencia versionada.
>     - F2: empresas y solicitudes completas, con CRUD, filtros, búsqueda, orden y paginación en la URL, archivado, cuotas y aislamiento entre usuarios (T2, T3), tanto en backend como en frontend.
>     - F3: ciclo de vida completo. `domain/application_status.py` con la tabla `ALLOWED_TRANSITIONS`; `application_status_changes` (historial append-only, `seq` como orden real); `ApplicationStatusService` (cambiar y deshacer, con `SELECT … FOR UPDATE`); `allowed_transitions` en `ApplicationRead`; en el frontend, el diálogo de cambio de estado, la línea de tiempo del historial y deshacer.
>     - F4: entrevistas y recordatorios. `interviews` (CRUD completo, hija de `applications`, sin `user_id` propio); `reminders` (raíz con `user_id`, FK compuesta opcional a `applications`, límite contado en todos los estados desde F11, [0011](docs/decisiones/0011-limite-de-recordatorios-en-todos-los-estados.md)); `services/notifications/` con `NotificationChannel` e `InAppChannel` (no-op, costura de RF-53; retirados en F12, [0012](docs/decisiones/0012-el-canal-de-aviso-va-en-la-entrega.md)); crear/listar/completar/descartar para recordatorios, y borrar desde F11 (0011); sin editar. En el frontend, ambas secciones viven embebidas en el detalle de la solicitud, y la sugerencia de RF-42 (proponer `interviewing` al programar una entrevista) usa `allowed_transitions`. **Los recordatorios no tienen página ni ruta propias en F4** (decisión [0005](docs/decisiones/0005-recordatorios-sin-pagina-global-en-f4.md)): se crean y ven filtrados por solicitud; la API ya admite un listado global y un recordatorio suelto (`application_id` nulo), pensando en F5.
>     - F5: dashboard y exportación CSV. `GET /dashboard` (`app/domain/dashboard.py`, `app/services/dashboard_service.py`, `app/schemas/dashboard.py`) agrega en una sola respuesta el recuento por estado (RF-60), los envíos por semana en las últimas 12 semanas (RF-61), la tasa de respuesta (RF-62, `null` con menos de 5 solicitudes enviadas por RF-66), las próximas entrevistas y los recordatorios pendientes o vencidos (RF-63) y las solicitudes sin actividad (RF-64); cada lista trae un vistazo de 5 elementos y su total. Las métricas de **estado actual** excluyen las solicitudes archivadas y las que retratan **lo ocurrido** las incluyen (detalle en `docs/arquitectura/index.md`). `GET /applications/export` (RF-70) vuelca a CSV todas las solicitudes del usuario, archivadas incluidas, con los códigos en crudo de los enumerados; registrado antes de `/{application_id}` en el router para que `export` no se lea como un UUID. En el frontend, `features/dashboard/` (seis widgets, `recharts` como dependencia nueva) y `pages/DashboardPage.tsx`, que sustituye a `/applications` como página de inicio (`/` redirige a `/dashboard`); `pages/RemindersPage.tsx` en `/reminders` cierra el hueco que dejó la decisión [0005](docs/decisiones/0005-recordatorios-sin-pagina-global-en-f4.md) (filtro por estado en la URL, paginación, crear/completar/descartar, mismo alcance que ya tenía la API); `ReminderFormDialog` ya no exige un `applicationId` fijo: si se omite, deja elegir la solicitud o dejar el recordatorio sin ligar (RF-50). Botón "Exportar CSV" en `ApplicationsPage` vía `apiClient.getBlob()` y `shared/lib/download.ts`.
>     - F6: integración continua. `.github/workflows/ci.yml`, 4 jobs en cada push/PR a `main`: `backend-lint` (ruff + mypy, nativo con `uv`, sin Docker), `backend-tests` (`compose.test.yml`, la suite de pytest), `frontend` (eslint, `tsc -b`, vitest, build) y `docs` (`mkdocs build --strict`). `.env.test.example` es la plantilla versionada de `.env.test`, antes inexistente.
>     - F8: revisión final. F8.1 auditó la especificación completa frente al código y no encontró huecos. F8.2 (funcionalidad): `GET/PATCH /me/preferences` (idioma y umbral de "sin actividad" de RF-64, entre 1 y 90 días); moneda del salario como lista cerrada EUR/USD/GBP/CHF (antes texto libre, R5); `app/scripts/check_performance.py` para medir RNF-10/RNF-11 a mano; auditoría de mensajes de error y de pruebas adversas; y borrado de cuenta (`DELETE /me`, RNF-40), que estaba pospuesto `[C]` y se decidió construir aquí ([0008](docs/decisiones/0008-borrado-de-cuenta-en-f8.md)). F8.3 (diseño de la interfaz): logo y paleta indigo/slate/zinc con contraste WCAG AA medido en los colores de estado; tema claro/oscuro por navegador (`app/providers/ThemeProvider.tsx`, no en la cuenta); diseño adaptable con menú hamburguesa por debajo de `lg`; diálogos que caben en pantalla; login y registro rediseñados (`AuthLayout` + `AuthShowcase`); gráficas con `ResponsiveContainer` y tooltip propio; estados de carga, vacío y error comunes (`shared/components/common/{EmptyState,ErrorState,Skeletons}.tsx`, y `ApplicationLoadError` para separar un 404 de otro fallo); formularios, detalle y preferencias a ancho completo dentro de `Card`; accesibilidad (`aria-describedby` en cada error de campo, `<html lang>` sincronizado con i18next, título de pestaña por página con `shared/hooks/useDocumentTitle.ts`, enlace "Saltar al contenido" y landmarks); y `queryClient` sin reintentos en los 4xx.
>     - F9, infraestructura de la v2 (validada de punta a punta con un esqueleto vertical que ya se retiró; queda en el historial, commit `993e719`):
>         - **Correo:** el servicio `mailpit` (solo desarrollo), `app/infra/email/` (`EmailSender` con las implementaciones SMTP, desactivada y de pruebas; la SMTP clasifica cada fallo en "no salió" o "no se sabe") y `app/scripts/send_test_email.py`.
>         - **Cola:** los servicios `valkey` y `worker`, `app/infra/queue/` (`JobQueue` con `SaqJobQueue` e `InMemoryJobQueue`), `app/worker.py`, `app/jobs/` y la cola creada en el `lifespan` de `main.py` (`get_job_queue` en `deps.py`).
>         - **Ficheros:** el volumen `files_data` (montado en `/data/files` en `api` y `worker`) y `app/infra/storage/` (`FileStorage` con `LocalFileStorage`: escritura atómica, claves encerradas en la raíz y límite de tamaño contado al escribir).
>         - **PDF:** `app/infra/pdf/` (`PdfRenderer`; `WeasyPrintRenderer` con Jinja2 y `TemplateOnlyFetcher` contra SSRF, en `weasyprint_renderer.py`, que solo importa el `worker`) y las librerías de sistema de WeasyPrint en la imagen.
>         - **Sin usar todavía:** `get_job_queue` y `get_file_storage` de `deps.py` no los usa aún ningún endpoint, y ningún código genera PDFs. El primer trabajo del `worker` llegó con F11 (email de recuperación de contraseña).
>     - F10, manual de producción: `manual/` (Docusaurus 3.10, español por defecto e inglés en `i18n/en/`) con uso (una página por tarea del MVP), despliegue (servicios, variables, correo, copias de seguridad; la receta de producción llega con F7) y API (guía de integración + referencia generada del OpenAPI). Servicio `manual` (3001) y job `manual` en la CI.
>     - F11 (cerrada con el `qa-verifier`, que encontró el rate limit de `/auth/*` saltable por la URL y la espera con Valkey caído; al verificar en el navegador apareció además el login roto por `expose_headers`, ver trampas):
>         - `GET /api/v1/meta` (público: `email_enabled`) y el router `public` de `api/v1/router.py`, con la lista blanca de rutas sin sesión escrita en la prueba T1.
>         - **Recuperación de contraseña** (RF-03): la entrega de emails de SuperTokens encola `send_password_reset_email` (`core/auth_emails.py`), y el `worker` lo envía con `AuthEmailService` y las plantillas de `templates/email/`, en el idioma de la cuenta o, si no, en el de la interfaz. Al recuperarla se revocan todas las sesiones. En el frontend, `/forgot-password`, `/reset-password` y, en Preferencias, el mismo enlace para **cambiar** la contraseña.
>         - **Verificación de email** (RF-05, RF-06): receta `emailverification` en modo `OPTIONAL`; el registro encola `send_verification_email` (override de `sign_up_post`) y el reenvío pasa por `QueuedVerificationEmail`. `require_verified_email` (`deps.py`) da 403 `email_not_verified` y, ante un "no" del token, vuelve a preguntar al core; sin correo no exige nada, porque nadie podría verificar ([0013](docs/decisiones/0013-sin-correo-no-se-exige-verificar-el-email.md)). La primera ruta que la usa es la subida de documentos de F13 (los avisos de F12 comprueban la verificación en el barrido, no con esta dependencia). En el frontend, `EmailVerificationBanner` en `AppLayout` (oculto sin correo), la tarjeta `EmailVerificationCard` de Preferencias (estado siempre visible y reenvío) y `/verify-email`.
        - **Zona horaria** (RF-07, A39): `users.timezone` con un nombre IANA validado en `domain/user.py` (`is_valid_timezone`), editable en `PATCH /me/preferences`. El frontend envía la del navegador si la cuenta no tiene (`useDetectTimezone` en `AppLayout`) y Preferencias la muestra con un buscador (`FormCombobox`, nuevo en `shared/components/form/`). La usan los avisos de F12: la hora del resumen semanal y las fechas de cada email.
        - **Límites visibles** (RF-140…143): `domain/limits.py` (`LimitKey`, `LIMIT_RULES`), `LIMIT_*` en la configuración, excepciones por cuenta en `user_limit_overrides` con `scripts/set_user_limit.py` (también "sin límite", salvo en almacenamiento e IA), y `LimitService`, que usan los services de solicitudes, empresas y recordatorios. `LimitReachedError` responde `{detail, code, limit, used}` (`AppException.extra`). `GET /me/usage`; en el frontend, `features/usage/` (tarjeta **Uso de la cuenta** en Preferencias y `LimitWarning` en los formularios de creación desde el 80 %).
        - **Rate limiting** (RNF-04): `infra/rate_limit/` (`limits` sobre Valkey, ventana deslizante), reglas en `domain/rate_limits.py`, el middleware `api/auth_rate_limit.py` para `/auth/*` (por IP, email o usuario) y `enforce_api_rate_limit` en el router `protected` (600/min por usuario). 429 `rate_limited` con `Retry-After`; con Valkey caído, deja pasar (y deja de consultarlo 30 s). IP real con `TRUSTED_PROXIES` (`core/client_ip.py`).
        - Selector de idioma en las pantallas de acceso (RF-08, `shared/components/LanguageSwitcher.tsx`), recordado en el navegador (`browserLanguage()` de `shared/i18n/i18n.ts`).
>     - F12 (cerrada con el `qa-verifier`, que encontró el mismo envío ejecutado dos veces a la vez saliendo dos veces; ver trampas):
        - `domain/notifications.py` y `notification_deliveries` (reclamo con clave única `(user_id, kind, channel, dedupe_key)`, `channel` hoy solo `email`, estados `claimed`/`sent`/`failed`/`unknown`, `claimed_at` y `next_attempt_at`).
        - `NotificationDeliveryService`: reclamar y confirmar, encolar `send_notification` (un intento), enviar (por id **y** `user_id`, con el contenido de un `NotificationComposer` por tipo) y dar por `unknown` los reclamos abandonados. Los compositores de cada tipo los reúne `composers_for` (`services/notifications/`).
        - Barridos como `CronJob` de SAQ (`jobs/notifications.py`), ninguno (tampoco la limpieza) sin SMTP: reclamos abandonados y entrevistas próximas (cada 5 minutos), recordatorios vencidos (cada minuto), y solicitudes sin actividad y resumen semanal (cada hora).
        - **Recordatorio vencido** (RF-80): `services/notifications/reminder_due.py` (`ReminderDueSweep`, ventana de 24 h sobre el momento del aviso, solo cuentas verificadas; `ReminderDueComposer`), con antelación opcional (`reminder_notice_hours`: al vencer, 1 hora o 1 día antes), fechas en la zona y el idioma del usuario (`domain/dates.py`) y plantillas `templates/email/reminder_due/`. La costura `NotificationChannel` de F4 se retiró: el canal va en la entrega ([0012](docs/decisiones/0012-el-canal-de-aviso-va-en-la-entrega.md)).
        - **Entrevista próxima** (RF-81): `services/notifications/interview_upcoming.py`, cada 5 minutos, con la antelación de `interview_notice_hours`. La clave lleva la hora en segundos UTC: mover la entrevista vuelve a avisar (B8). El bucle común de los barridos es `ClaimingSweep` (`services/notifications/sweep.py`).
        - **Solicitudes sin actividad** (RF-83): `services/notifications/stale_applications.py`, cada hora, con el umbral de `stale_after_days` y los estados de espera del dashboard. Un aviso por solicitud y periodo de inactividad (la clave lleva `last_activity_at`), agrupados en **un email por usuario y pasada**: `send_notification` recibe una lista de entregas y el compositor devuelve una `Composition` con las que cubre.
        - **Resumen semanal** (RF-82): `services/notifications/weekly_digest.py`, cada hora; sale el lunes desde las 8:00 en la zona del usuario (`digest_key_if_due`, clave con la semana ISO local), con lo del dashboard, también si no hay nada. La hora local se calcula en Python, no en SQL (Postgres podría no conocer algún nombre de zona).
        - **Baja con un clic** (RF-85): token HMAC de (usuario, tipo) con `APP_SECRET` (`domain/unsubscribe.py`), `GET`/`POST /api/v1/notifications/unsubscribe` en el router `public` (30/min por IP; el `GET` no aplica nada), cabeceras `List-Unsubscribe` y `List-Unsubscribe-Post` en cada aviso y la página `/unsubscribe` del frontend, que pide confirmar.
        - **Limpieza de entregas** (cada día a las 3:30 UTC): borra las terminadas de más de 90 días (`DELIVERY_RETENTION`), salvo las de inactividad cuya clave sigue siendo la de la solicitud, que protegen para siempre a una solicitud que sigue parada. Sin historial visible para el usuario.
        - Preferencias `notify_*`, `reminder_notice_hours` e `interview_notice_hours` en `users` y `PATCH /me/preferences`; en el frontend, `features/notifications/` con la tarjeta **Avisos por email** de Preferencias (cada interruptor guarda al momento).
>     - F13 (cerrada con el `qa-verifier`, que encontró dos carreras entre borrar un documento y asignarlo que acababan en 500: la FK salta en el `flush`, no solo en el `commit`; diseño y trampas en `docs/arquitectura/ficheros.md`): biblioteca de CVs y cartas en PDF y su asociación a las solicitudes. Backend: `documents` (`DocumentService`, `DocumentRepository`, `domain/documents.py`), `POST`/`GET /documents`, `GET`/`PATCH`/`DELETE /documents/{id}`, `GET /documents/{id}/file`, `…/archive` y `…/unarchive`; la subida es el PDF **en crudo** (`Content-Type: application/pdf`, `kind` y `name` en la query), exige email verificado y tiene su propio rate limit; los límites `documents` y `storage_bytes` (en bytes, sin "sin límite"; `LimitRule.unit`); `GET /meta` publica `max_document_bytes`. En `applications`, `job_description`, `cv_document_id` y `cover_letter_document_id` (solo en `ApplicationDetailRead`; FK compuestas `NO ACTION`; borrar un documento en uso da 409 `document_in_use`). `OrphanFileService` (cada día a las 4:15 UTC, `jobs/files.py`) y `AccountService.delete_account`, que borra los ficheros de la cuenta después del commit. Frontend: `features/documents/` (página `/documents`, visor, renombrar, archivar, borrar), `FormFileInput` y, en el formulario y el detalle de la solicitud, la sección **Oferta y documentos enviados**.
>     - F14 (en construcción; paso 1 de 5): perfil profesional con sus datos básicos. `profiles` (`models/profile.py`, `ProfileRepository`, `ProfileService`, `domain/profile.py`), `GET` y `PUT /profile` (la fila se crea al primer guardado con `ON CONFLICT`; enlaces solo `http`/`https`). En el frontend, `features/profile/` y la página `/profile` en el menú (**Perfil**). Las decisiones del usuario para el resto de la fase: reordenar con arrastrar y soltar (`dnd-kit`) y cuatro diseños de CV, tres aptos para ATS y uno gráfico marcado como no apto.
> - **No existe todavía:**
>     - F7, la puesta en producción real (orden invertido a petición del usuario; ver [0009](docs/decisiones/0009-f8-antes-que-f7.md)), en espera de servidor.
>     - **El resto de la v2**: lo que queda de F14 (entradas del perfil, habilidades e idiomas, plantillas y generación) y F15–F17 (IA, Kanban y calendario). De eso solo existe su diseño (§2). Ninguno de sus servicios, comandos ni carpetas está en el repositorio: no los ejecutes ni los busques hasta que se construya su fase.

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
| `docs/arquitectura/v2.md` | **v2 (diseño; construida hasta F13):** decisiones A18–A42, modelo de datos, flujos, consistencia entre almacenes e invariantes 9–18 |
| `docs/arquitectura/{segundo-plano,ficheros,ia,limites-y-abuso}.md` | **v2:** cada tema con sus trampas y sus pruebas adversas (B, D, I, L); la ampliación de autenticación está en `autenticacion.md` §8 (T9–T15) |
| `manual/` | Documentación de **producción** en Docusaurus, es + en: manual de uso, despliegue y API (guía + referencia generada del OpenAPI). Reglas en `manual/README.md` ([0010](docs/decisiones/0010-docusaurus-para-la-documentacion-de-produccion.md)) |

**Si el código y un documento no coinciden, no se corrige el documento sin más.** Primero se averigua si el diseño evolucionó (y se actualiza el documento dejando constancia) o si la implementación se lo saltó (y entonces es un fallo del código).

## 3. Stack y servicios

| Servicio | Puerto | Notas |
|---|---|---|
| `db` | 5432 | Postgres 17, datos de la app, gestionados por Alembic |
| `api` | 8000 | FastAPI + SQLAlchemy async + Alembic (python 3.12, uv). `/docs` = OpenAPI. |
| `frontend` | 5173 | React 19 + TS + Vite 8, TanStack Query, react-hook-form + zod, Tailwind v4 + shadcn/ui, i18next |
| `docs` | 8001 | MkDocs Material **fijado a la 9** (MkDocs 2.0 rompe plugins y temas) |
| `supertokens`, `supertokens-db` | — | Core de auth **fijado a 12.2.0** (debe implementar la CDI de `supertokens-python`), con **su propia** instancia de Postgres; no se publican puertos. Access token de 5 min ([0002](docs/decisiones/0002-access-token-de-5-minutos.md)). |
| `valkey` | — | Valkey 9.1 (Redis libre): cola de SAQ y, desde F11, rate limit. Sin puertos publicados. `VALKEY_URL` es obligatoria: sin ella `api` no arranca |
| `worker` | — | Misma imagen, código y `.env` que `api`, con otro comando: `saq --quiet app.worker.settings` envuelto en `watchfiles` (se reinicia solo al cambiar un `.py`). No aplica migraciones |
| `manual` | 3001 | Docusaurus (manual de producción). El servidor de desarrollo sirve **un solo idioma** (español); el inglés se arranca aparte con `--locale en` |
| `mailpit` | 8025 | **Solo desarrollo** (F9). Captura todo el correo (SMTP interno en `mailpit:1025`) y no envía nada fuera. En producción el SMTP lo configura quien despliega con `SMTP_*` y `EMAIL_FROM`; sin `SMTP_HOST`, la app arranca y no envía emails (RNF-34). |

Usa siempre `localhost` y nunca `127.0.0.1` (ver trampas).

Todos los servicios de la v2 ya existen. Detalle en `docs/arquitectura/servicios-y-estructura.md` §8.

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
docker compose exec api python -m app.scripts.send_test_email tu@example.com  # prueba el SMTP configurado (en desarrollo llega a Mailpit)
docker compose logs -f worker                                              # trabajos procesados y sus errores
docker compose exec api python -m app.scripts.set_user_limit ana@example.com [clave|all] [valor | --unlimited | --reset]  # límites de una cuenta (RF-143)

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
docker compose run --rm --no-deps manual npm run check-i18n               # cada página del manual en es y en
docker compose run --rm --no-deps manual npm run build                    # manual completo (los dos idiomas); falla ante enlaces rotos
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

**En la v2** la regla se amplía (servicios y estructura §8.3): lo que habla con otro sistema externo (disco, Valkey, SMTP, IA, PDF) vive en `infra/` detrás de una interfaz, y los trabajos del `worker` son funciones finas en `jobs/` que solo llaman a un service. De `infra/` existen `email/`, `queue/`, `storage/` y `pdf/`. Las implementaciones de `infra/` se eligen en quien cablea (`build_email_sender(settings)`), nunca en un service.

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
- **Frontend:** alias `@/`; formularios con `shared/components/form/*`; filtros de listados en la URL; nunca `fetch` fuera de `apiClient`; estados de carga, vacío y error con `shared/components/common/{Skeletons,EmptyState,ErrorState}.tsx` (un 404 se distingue de otro fallo, como en `ApplicationLoadError`); título de página con `shared/hooks/useDocumentTitle.ts`.
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
11. (v2, n.º 11 de `v2.md` §8) Se encola siempre **después** del `commit`, nunca dentro de la transacción: el trabajo lleva ids y el `worker` ve la fila ya confirmada. Si encolar falla, la fila ya existe y un barrido decide qué hacer con ella (reencolarla o, en un aviso, darla por `unknown`).
12. (v2, n.º 12) Un email de aviso por (usuario, tipo, motivo): se reclama y se **confirma** en `notification_deliveries` antes de hablar con el SMTP, solo se reintenta lo que con seguridad no salió (`failed`), y un `unknown` nunca se reenvía. `deliver` bloquea las entregas con `FOR UPDATE SKIP LOCKED` hasta el commit para que el mismo envío ejecutado dos veces a la vez salga una sola.
13. (v2, n.º 18) Todo endpoint sin sesión está en la lista blanca de la prueba T1 (`GET /meta`, la baja de avisos…).
14. (v2, n.º 9) Postgres es la única fuente de verdad: Valkey y el volumen de ficheros son derivados o transitorios.
15. (v2, n.º 10) Ningún documento `ready` apunta a un fichero inexistente: se escribe el fichero antes que la fila y se borra la fila antes que el fichero. Solo pueden sobrar ficheros, y el barrido de huérfanos los limpia.
16. (v2, n.º 16) Las funciones con coste comprueban el email verificado en el backend (`require_verified_email`; sin correo no se exige, 0013).
17. (v2, n.º 17) Las cuotas con coste se comprueban con la fila del usuario bloqueada (`UserRepository.lock`), para que dos subidas simultáneas no pasen juntas del límite.

La v2 añade los invariantes 9–18 de `docs/arquitectura/v2.md` §8 (su numeración choca con la de aquí desde el 9: aquí se indica el número de `v2.md`). Se copian al construir la fase que los hace efectivos: faltan los de IA y claves (13–15), y la parte de IA de los números 16 y 17.

## 8. Trampas conocidas

- **Dependencias que "no se instalan".** `api_venv` (volumen con nombre) y `/app/node_modules` (volumen anónimo) **no se actualizan al reconstruir la imagen**. Instala dentro del contenedor **en marcha, con `exec`**. `docker compose run --rm frontend npm install` crea un contenedor nuevo con su propio `node_modules`: el paquete se pierde y el contenedor `frontend` nunca lo ve, aunque `package.json` sí cambie. Tras un `git pull` con dependencias nuevas: `docker compose up --build -V` y `docker compose run --rm api uv sync`.
- **Variables nuevas del `.env` no se aplican con `restart`.** `env_file` se lee al **crear** el contenedor: usa `docker compose up -d --force-recreate <servicio>`.
- **El logout no invalida al instante un access token ya emitido.** Se valida sin consultar al core, así que una copia sigue sirviendo hasta caducar (5 min). El refresh token sí queda revocado ([0002](docs/decisiones/0002-access-token-de-5-minutos.md)).
- **Endpoints nuevos: dentro del router `protected`** de `api/v1/router.py`, salvo que deban ser públicos. La prueba T1 lee las rutas del OpenAPI y falla si alguno responde sin sesión; los públicos (`health`, `meta`, la baja de avisos) están escritos en la prueba con lo que responde un `GET` sin sesión.
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
- **Pestaña oculta durante una verificación en vivo con navegador automatizado.** Con la pestaña en segundo plano, el navegador pausa `requestAnimationFrame` (así que una animación de cierre de diálogo no termina de correr) y TanStack Query deja de reintentar hasta que vuelve el foco. Un diálogo que parece no cerrarse o una petición que parece colgada puede ser solo eso, no un bug: mantén la pestaña visible al verificar.
- **En SAQ, `retries` cuenta intentos totales, no reintentos.** Un trabajo se repite mientras `retries > attempts`, y `attempts` ya vale 1 tras el primero: `retries=1` (el valor por defecto) es un solo intento y `retries=0` significa lo mismo. Por eso `JobQueue.enqueue` habla de `max_attempts`. Y SAQ mezcla en el mismo `**kwargs` sus opciones (`timeout`, `key`…) y los argumentos de la función: `SaqJobQueue` pasa los argumentos en `kwargs=` para que no se confundan.
- **El manual es otro sitio con otro público.** Cada cambio que ve el usuario, que toca el despliegue o que cambia una convención de la API actualiza `manual/` en español **y** en inglés en el mismo commit (tabla en `.claude/agents/docs-writer.md`). `npm run check-i18n` falla si una página existe en un solo idioma. Los nombres de botones se copian de `frontend/src/shared/i18n/locales/`. Nunca se copia texto entre `docs/` y `manual/`: uno explica y el otro enlaza.
- **La referencia de la API del manual sale de una copia derivada.** `manual/scripts/prepare-openapi.mjs` copia `docs/referencia/openapi.json` añadiendo un servidor `{apiUrl}`: el contrato del backend no declara `servers` (Swagger debe llamar a su propio origen) y sin ellos los ejemplos apuntaban al manual. No edites la copia ni la salida (`.openapi/`, `docs/api/referencia/`): se regeneran en cada `start` y `build`.
- **Textos del tema de OpenAPI.** `write-translations` no los extrae (viven en el paquete compilado): su traducción al español está a mano en `manual/i18n/es/code.json`. Y no versiones los JSON de la barra lateral de la API que genera `write-translations`: son una copia del OpenAPI que envejece.
- **Un trabajo nunca lleva un token de acceso.** Valkey guarda los trabajos en disco (`appendonly`). SuperTokens entrega a su servicio de email el enlace de recuperación ya hecho, pero el trabajo encolado lleva solo ids y el `worker` genera otro enlace al enviar (`IdentityRepository.create_password_reset_link`). Una prueba comprueba los argumentos exactos del trabajo.
- **Emails de SuperTokens: la cola se pasa como función.** `init_supertokens(job_queue=…)` recibe una función porque la cola se crea después, en el `lifespan`. En las pruebas, el fixture `real_auth_client` pone una `InMemoryJobQueue` en `app.state.job_queue`. El `worker` inicializa el SDK sin cola y nunca atiende `/auth/*`.
- **Límites: el consumo se cuenta, no se guarda.** `LimitService` hace `COUNT` sobre las tablas reales; no añadas un contador que se incremente, porque un borrado en cascada o un script lo desincronizaría para siempre. Y el código de error es contrato: `LimitKey.REMINDERS` responde `reminders_limit_reached`, el del MVP. Los recordatorios cuentan en cualquier estado (0011): completarlos no libera espacio, borrarlos sí. Los mensajes del frontend usan `t(errorMessageKey(e), errorMessageParams(e))` para poder decir el límite. Un límite nuevo con coste (almacenamiento, IA) **no** admite "sin límite": `LimitRule.allows_unlimited` es falso por defecto y el CHECK `unlimited_only_where_allowed` de la BD lo impone; al añadir una clave, la migración tiene que rehacer ese CHECK.
- **`refetchOnWindowFocus` está desactivado en el `queryClient`** y las respuestas se guardan 5 minutos. Una consulta que deba refrescarse al volver a la pestaña (como `useEmailVerified`) tiene que pedirlo explícitamente, con `staleTime: 0`.
- **Zonas horarias: nombres antiguos del navegador.** Los navegadores dan 18 zonas con su nombre antiguo (`Asia/Calcutta`, `Europe/Kiev`), que la tzdata de Debian ya no trae. Por eso el backend depende del paquete `tzdata` de Python: sin él, la detección automática falla con 422 en esas zonas sin que nadie lo note.
- **Rate limiting y middlewares.** `AuthRateLimitMiddleware` va entre el de SuperTokens y CORS: por fuera de SuperTokens para alcanzar `/auth/*` antes que él, y por dentro de CORS para que el 429 lleve sus cabeceras. Lee el cuerpo para limitar por email y **lo vuelve a inyectar**: si se lo comiera, SuperTokens respondería `FIELD_ERROR` a un inicio de sesión correcto. Y busca la regla con `rules_for`, nunca por la ruta exacta: SuperTokens atiende también `/auth/public/signin` y `/auth/signin/`, y con una coincidencia exacta cambiar la URL se saltaba el límite. En las pruebas el rate limit está desactivado (`app.state.rate_limiter` es `DisabledRateLimiter` sin lifespan); las que lo prueban ponen un `LimitsRateLimiter("async+memory://")`. En producción detrás de un proxy, `TRUSTED_PROXIES` es obligatoria o todos los usuarios comparten la IP del proxy.
- **Nunca `expose_headers` en el `CORSMiddleware`.** Starlette aplica esa lista a todas las respuestas y pisa el `Access-Control-Expose-Headers` de SuperTokens: el navegador deja de leer `front-token` y el login responde `OK` sin crear sesión (pasó en F11). Una cabecera que el navegador deba leer se expone en su propia respuesta, como `Retry-After` con `retry_after_headers`. Lo vigila `tests/api/test_cors.py`.
- **Avisos por email: el contenido no decide si se envía.** El barrido reclama (`NotificationDeliveryService.claim`, con commit) y encola; `send_notification` solo envía lo que sigue en `claimed`. Un tipo nuevo de aviso es un módulo en `services/notifications/` (su consulta y su clave sobre `ClaimingSweep`, y un `NotificationComposer` registrado en `composers_for`: `SingleDeliveryComposer` si cada email es un motivo), y un canal nuevo, un valor de `DeliveryChannel` (0012), nunca un `channel` en el recordatorio. Una pasada del barrido lee candidatos por páginas hasta agotarlos: si leyera una sola, las cuentas sin verificar la ocuparían. No metas reintentos en la cola (`max_attempts=1` siempre) ni reenvíes una entrega `unknown`. Los barridos reciben "ahora" como parámetro: el reloj real solo se lee en `jobs/notifications.py`.
- **El mismo envío ejecutado dos veces a la vez.** SAQ puede lanzar de nuevo un trabajo que acaba de empezar, y comprobar `claimed` al empezar no basta: las dos ejecuciones lo ven antes de que ninguna marque `sent`. `NotificationDeliveryService.deliver` lee las entregas con `FOR UPDATE SKIP LOCKED` y no suelta el bloqueo hasta el commit final, SMTP incluido (`tests/services/test_notification_adversarial.py`). No saques el envío fuera de esa transacción ni quites `lock=True`.
- **Cabeceras largas en un email.** Una URL sin espacios de más de 78 caracteres (la de `List-Unsubscribe`) salía codificada en RFC 2047 y los clientes de correo no la reconocían. `SmtpEmailSender` serializa con líneas de hasta 998. Y el `FakeSmtpServer` decodifica al parsear: para probar cómo viaja una cabecera, mira `server.raw`, no `server.messages`.
- **`APP_SECRET` es obligatoria** desde F12 (firma los enlaces de baja). Tras un `git pull`, añádela al `.env` y recrea `api` y `worker` con `--force-recreate`: sin ella la API no arranca. Cambiarla invalida los enlaces de baja ya enviados.
- **Una sola instancia de `verify_session()`.** `get_current_user` y `require_verified_email` dependen de `_session_dependency` (`deps.py`): FastAPI solo cachea una dependencia por petición si es el mismo objeto, y con `verify_session()` escrito en cada sitio la sesión se validaría dos veces. Desde F13, `as_user` sustituye también `require_verified_email` (el usuario de prueba tiene el email verificado): lo que exige la verificación se prueba contra el core real con `real_auth_client` (`tests/api/test_email_verification.py` y la subida de `test_documents.py`).
- **Páginas que consumen un token del enlace, una sola vez.** En desarrollo `StrictMode` monta dos veces los efectos: sin la guarda de `useRef` de `VerifyEmailPage`, la segunda llamada recibe "enlace no válido" y es lo que se pinta.
- **Borrar ficheros por prefijo, sin barra final.** `delete_prefix` rechaza un segmento vacío (así un id vacío nunca se vuelve `users`): `user_prefix` devuelve `users/{id}`, no `users/{id}/`. Con la barra, borrar la cuenta dejaba sus ficheros y solo quedaba un error en el log.
- **Un `<form>` dentro de otro, aunque esté en un portal.** El diálogo de subida se abre dentro del formulario de la solicitud: en React el `submit` sube por el árbol de componentes, no por el DOM, así que enviar la subida enviaría también la solicitud. `UploadDocumentDialog` corta con `event.stopPropagation()`; cualquier diálogo con formulario que se abra desde otro formulario necesita lo mismo.
- **Claves de traducción: mismas en `es.json` y `en.json`.** `locales.test.ts` compara las dos; una clave que falta o que cae en otro bloque se pinta en crudo sin que falle nada más.
- **FK a `documents` con `NO ACTION`, nunca `RESTRICT`.** `RESTRICT` se comprueba fila a fila: el borrado en cascada de una cuenta (solicitudes y documentos en la misma sentencia) fallaría si Postgres borrara antes el documento que la solicitud que lo apunta. `NO ACTION` comprueba al final de la sentencia (v2 §4, trampa).
- **Subidas en crudo, nunca `UploadFile`.** Con `multipart/form-data`, Starlette guarda el fichero entero en un temporal antes de llamar al endpoint: un cuerpo de 10 GB llenaría el disco aunque luego se rechazara por tamaño. `POST /documents` recibe el PDF en crudo y `DocumentService` lee `request.stream()` cortando al pasar del máximo (D2). El nombre visible pasa por `sanitize_name` y nunca llega al disco: la ruta es `users/{user_id}/documents/{id}.pdf`.
- **WeasyPrint solo en el `worker`.** `app.infra.pdf` exporta solo la interfaz; la implementación (`app.infra.pdf.weasyprint_renderer`) la importa `worker.py`. WeasyPrint no publica tipos: sus imports llevan `# type: ignore[import-untyped]`.
- **La cola de SAQ se crea dentro del event loop** (el `lifespan` de `main.py`, o una por prueba), nunca al importar un módulo de la API: guarda primitivas de `asyncio` que quedan ligadas al primer loop que las usa, y en los tests (un loop por prueba) fallaría desde la segunda.
- **Encolar puede fallar después del commit.** Con Valkey caído, encolar tarda unos 4 s y lanza `QueueUnavailableError`. Un service que encola tras confirmar una fila `pending` no debe convertir eso en un 500: la fila ya existe y el barrido de pendientes la reencola (v2 §3). El `worker` sí se recupera solo cuando Valkey vuelve, y los trabajos encolados sobreviven a un reinicio de Valkey (`--appendonly yes`).
- **`changed_at` exige zona horaria, pero el selector de fecha solo captura un día.** El schema (`AwareDatetime`) rechaza con 422 un datetime "naive", y `FormDatePicker` (heredado de F2) solo devuelve `"yyyy-MM-dd"`. Combinar ese día con medianoche local haría que elegir "hoy" cayera antes del último cambio ya registrado (que tiene la hora real de "ahora") y el backend lo rechazaría con 422 `changed_at_before_last_change`, de forma confusa para quien solo quería decir "ahora mismo". `applicationStatusChangeService.toChangedAt()` combina el día elegido con la **hora local actual**, no medianoche; probado en `applicationStatusChange.service.test.ts`.

## 9. Agentes

Están en `.claude/agents/`. Se invocan explícitamente al cerrar una feature o una fase; no corren solos.

| Agente | Cuándo |
|---|---|
| `docs-writer` | Al cerrar una feature, un endpoint o una migración, o si el código parece haber divergido del diseño. Mantiene `docs/` (desarrollo) y, desde F10, `manual/` (producción, es + en) en el mismo commit que el código |
| `qa-verifier` | Antes de dar por terminado un bloque de trabajo: tipos, estilo, tests (incluidos los adversos, también los de la v2 de cada documento de tema) y verificación en vivo |

## 10. Fases

| Fase | Contenido |
|---|---|
| ✔ Entorno | Docker de desarrollo, health, sitio de documentación |
| ✔ F0 | Esqueleto vertical desechable: crear y listar solicitudes sin auth, atravesando todas las capas |
| ✔ F1 | SuperTokens (core + BD), `users`, `get_current_user`, router protegido, login y registro, rutas protegidas |
| ✔ F2 | Empresas y solicitudes: CRUD, filtros, paginación, archivado, pruebas de aislamiento, OpenAPI en docs |
| ✔ F3 | Ciclo de vida: historial, transiciones, deshacer, `allowed_transitions` |
| ✔ F4 | Entrevistas y recordatorios (`in_app`; la costura `NotificationChannel` se retiró en F12, 0012) |
| ✔ F5 | Dashboard (`GET /dashboard`), exportación CSV (`GET /applications/export`) y página global de recordatorios (`/reminders`) |
| ✔ F6 | CI con GitHub Actions (construida antes que F5, a petición explícita del usuario; ver [0006](docs/decisiones/0006-ci-antes-que-f5.md)) |
| ✔ F8 | Revisión final: auditoría de funcionalidades (sin huecos), preferencias de usuario, moneda cerrada, script de rendimiento, borrado de cuenta y diseño de la interfaz (paleta, tema claro/oscuro, adaptable, accesibilidad, estados de carga/vacío/error). Construida antes que F7, a petición explícita del usuario; ver [0009](docs/decisiones/0009-f8-antes-que-f7.md) |
| F7 | Puesta en producción real: `compose.prod.yml`, Nginx, variables de producción y despliegue efectivo. **En espera** hasta que haya un VPS; incluirá los servicios de la v2 que ya estén construidos y el rate limiting en Nginx con `TRUSTED_PROXIES` (lista en `docs/arquitectura/limites-y-abuso.md` §2) |
| ✔ F9 | **v2.** Infraestructura: correo (Mailpit + `EmailSender`), cola (Valkey + SAQ + `worker`), almacén (`files_data` + `FileStorage`) y PDF (WeasyPrint), validados con un esqueleto vertical desechable (cola → `worker` → PDF → disco → email) que ya se retiró |
| ✔ F10 | **v2.** Documentación de producción en Docusaurus (`manual/`, es + en): uso, despliegue y API, con el job `manual` en la CI |
| ✔ F11 | **v2.** Recuperación de contraseña, verificación de email, zona horaria, límites visibles y rate limiting |
| ✔ F12 | **v2.** Notificaciones por email (cuatro tipos, nunca dos veces por el mismo motivo), baja con un clic y preferencias de aviso |
| ✔ F13 | **v2.** Biblioteca de documentos (CVs y cartas en PDF) y descripción de la oferta |
| F14 | **v2.** Perfil profesional y CVs generados con plantillas |
| F15 | **v2.** IA: CV y carta adaptados, cuota gratuita fija y claves propias de proveedores habilitados |
| F16 | **v2.** Tablero Kanban |
| F17 | **v2.** Calendario y suscripción ICS |
