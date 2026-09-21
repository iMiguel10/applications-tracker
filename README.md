# Applications Tracker

Aplicación para el seguimiento de solicitudes de puestos de trabajo.

- **backend/**: API REST con FastAPI + SQLAlchemy (async) + Alembic, organizada en capas `api → services → repositories → db`.
- **frontend/**: React + TypeScript + Vite con arquitectura feature-based (TanStack Query, react-hook-form + zod, Tailwind v4 + shadcn/ui, i18next).
- **Auth**: SuperTokens (pendiente de integrar).
- **Base de datos**: PostgreSQL 17.

## Desarrollo

```bash
cp .env.example .env
docker compose up --build
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Documentación de la API | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

Las migraciones se aplican automáticamente al arrancar el contenedor `api`.

```bash
# Crear una migración
docker compose exec api alembic revision --autogenerate -m "descripcion"

# Instalar una dependencia del frontend (se instala en el volumen del contenedor)
docker compose run --rm frontend npm install <paquete>

# Añadir una dependencia del backend
docker compose exec api uv add <paquete>
```

## Tests y calidad

```bash
# Tests del backend contra una base de datos aislada
docker compose -f compose.test.yml up --build --abort-on-container-exit

# Lint y tipos
docker compose exec api ruff check .
docker compose exec api mypy app
docker compose exec frontend npm run lint
docker compose exec frontend npx tsc -b
```
