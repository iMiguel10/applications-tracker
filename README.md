# Applications Tracker

Un cuaderno de bitácora para la búsqueda de empleo: cada candidatura, cómo avanza (cambios de estado y entrevistas) y cuál es el próximo paso, para que ninguna se quede olvidada.

> **Estado:** en desarrollo. Terminadas F0 (esqueleto vertical), F1 (autenticación) y F2 (empresas y solicitudes); la siguiente es F3, ciclo de vida de la solicitud. [Ver fases](docs/producto/especificacion.md#11-alcance-por-fases).

## Qué resuelve

- **Todas las solicitudes en un sitio**, con filtros por estado, empresa, modalidad y fechas.
- **Historial real de cada proceso.** Cada cambio de estado queda registrado con la fecha en que ocurrió y se puede deshacer si fue un error.
- **Qué hacer hoy:** próximas entrevistas, recordatorios vencidos y candidaturas sin actividad.
- **Métricas honestas.** Cada porcentaje indica sobre cuántas solicitudes se calcula, y el sistema nunca da por descartada una candidatura que solo lleva tiempo sin respuesta.

## Stack

FastAPI · SQLAlchemy async · Alembic · PostgreSQL 17 · SuperTokens · React 19 · TypeScript · Vite · TanStack Query · Tailwind + shadcn/ui · Docker · MkDocs

## Decisiones destacadas

- **Arquitectura en capas verificable:** `endpoints → services → repositories`. Una sola regla la resume: *si habla con la base de datos, vive en `repositories/`*.
- **El estado de una solicitud es una máquina de estados** con historial append-only. Las transiciones solo las valida el backend, y la API le indica al frontend cuáles ofrecer.
- **Aislamiento entre usuarios en dos capas:** filtro obligatorio por usuario en cada consulta y claves foráneas compuestas que impiden, desde la propia base de datos, enlazar datos de otro usuario.
- **Autenticación delegada en SuperTokens**, con sesiones por cookies httpOnly, rotación de tokens y un core aislado con su propia base de datos.

Cada decisión, con la alternativa descartada y el porqué, está en la [documentación de arquitectura](docs/arquitectura/index.md).

## Arrancar

```bash
cp .env.example .env
docker compose up --build
```

| | |
|---|---|
| Aplicación | http://localhost:5173 |
| API (OpenAPI) | http://localhost:8000/docs |
| Documentación | http://localhost:8001 |

## Documentación

El sitio en `docs/` (MkDocs) contiene la especificación, la arquitectura, la autenticación y la bitácora de decisiones. La guía de trabajo del repositorio (comandos, convenciones e invariantes) está en [CLAUDE.md](CLAUDE.md).
