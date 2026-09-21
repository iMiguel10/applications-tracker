FROM python:3.12-slim

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

WORKDIR /app

USER appuser

# Copiamos únicamente los archivos de dependencias
# para aprovechar la caché de Docker.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Instalamos las dependencias sin instalar el proyecto.
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-install-project

# Copiamos el código de la aplicación
COPY --chown=appuser:appuser . .

RUN chmod +x /app/entrypoint.sh

# Utilizamos las herramientas instaladas por uv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
