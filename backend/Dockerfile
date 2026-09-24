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
