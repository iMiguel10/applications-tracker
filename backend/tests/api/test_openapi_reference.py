import json

from app.main import app
from app.scripts.export_openapi import REFERENCE_PATH

REGENERATE = "docker compose exec api python -m app.scripts.export_openapi"


def test_exported_openapi_reference_matches_the_api():
    # La referencia del sitio se genera de docs/referencia/openapi.json. Si un
    # endpoint o schema cambia sin regenerarlo, la documentación publicada miente.
    assert REFERENCE_PATH.exists(), (
        f"No existe {REFERENCE_PATH}. Genéralo con: {REGENERATE}"
    )

    exported = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))

    assert exported == app.openapi(), (
        f"docs/referencia/openapi.json está desactualizado. Regenéralo con: {REGENERATE}"
    )


def test_every_operation_has_a_summary_and_a_description():
    # Convención de docs/guias/documentar-la-api.md: nada llega a /docs sin
    # explicar qué hace.
    missing = [
        f"{method.upper()} {path}"
        for path, operations in app.openapi()["paths"].items()
        for method, operation in operations.items()
        if not operation.get("summary") or not operation.get("description")
    ]

    assert missing == [], f"Operaciones sin summary o description: {missing}"
