# Tres etapas (F7): `base` con lo común, `prod` para producción (compose.prod.yml,
# target: prod) y `dev`, la última, que es la que construyen compose.yml y
# compose.test.yml al no pedir ninguna.
FROM python:3.12-slim AS base

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Usuario no privilegiado. Es dueño de /app y del .venv para poder
# escribir cachés (pytest, ruff) y ejecutar `uv add` dentro del contenedor.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir /app \
    && chown appuser:appuser /app

# Librerías de sistema de WeasyPrint (A24, R9): sin ellas, `import weasyprint`
# falla al cargar libgobject. Las tipografías no se instalan aquí: viajan con cada
# plantilla (ficheros §7), para que el PDF no dependa de la imagen.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

# Raíz del almacén de ficheros (A21). Se crea con dueño appuser ANTES de montar el
# volumen: Docker copia el dueño del directorio de la imagen al crear un volumen
# vacío. Sin esto el volumen nace de root y la primera escritura falla con
# PermissionError (ficheros.md §3).
RUN mkdir -p /data/files && chown appuser:appuser /data/files

WORKDIR /app

USER appuser

# Utilizamos las herramientas instaladas por uv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000


# Producción: sin las dependencias de desarrollo y solo con lo que se ejecuta (sin
# tests/ ni evals/). El código va dentro de la imagen; no hay bind mounts.
FROM base AS prod

COPY --chown=appuser:appuser pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser alembic.ini entrypoint.sh ./
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser app ./app

RUN chmod +x /app/entrypoint.sh

# api: migraciones y uvicorn. El worker cambia el comando en compose.prod.yml.
# --no-proxy-headers: la IP real del cliente la decide core/client_ip.py con
# TRUSTED_PROXIES; uvicorn no debe reescribirla antes por su cuenta.
CMD ["/app/entrypoint.sh", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--workers", "2"]


# Desarrollo y pruebas: todas las dependencias, el código entero (también tests/
# y evals/) y, en compose.yml, el código montado encima con recarga en vivo.
FROM base AS dev

# Copiamos únicamente los archivos de dependencias
# para aprovechar la caché de Docker.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Instalamos las dependencias sin instalar el proyecto.
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-install-project

# Copiamos el código de la aplicación
COPY --chown=appuser:appuser . .

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
