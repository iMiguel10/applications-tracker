"""Exporta el esquema OpenAPI de la app a docs/referencia/openapi.json.

    docker compose exec api python -m app.scripts.export_openapi

La referencia de la API del sitio de documentación se genera de este fichero y
nunca se escribe a mano. tests/api/test_openapi_reference.py falla si el fichero
versionado no coincide con la app, así que hay que regenerarlo en el mismo commit
que cambia un endpoint o un schema.
"""

import json
import os
from pathlib import Path
from typing import Any

from app.main import app

# En el contenedor, docs/referencia está montado en /reference (compose.yml).
REFERENCE_PATH = Path(os.environ.get("OPENAPI_REFERENCE", "/reference/openapi.json"))


def render_openapi() -> str:
    schema: dict[str, Any] = app.openapi()
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    REFERENCE_PATH.write_text(render_openapi(), encoding="utf-8")
    print(f"OpenAPI exportado a {REFERENCE_PATH}")


if __name__ == "__main__":
    main()
