"""Exportación de todos los datos de una cuenta (issue #4, RGPD arts. 15 y 20).

Reglas puras: qué tablas salen y en qué fichero, qué columnas no salen nunca y
cómo se convierte cada valor a JSON. La prueba de completitud exige que cada tabla
del modelo esté aquí, exportada o excluida con su motivo: una tabla nueva con datos
de la persona no puede quedarse fuera sin que alguien lo decida.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any

# Versión del formato del `.zip`: se sube si cambia la forma de un fichero, no al
# añadir una columna (un lector debe ignorar lo que no conoce).
FORMAT_VERSION = 1

ACCOUNT_FILE = "account.json"
DOCUMENTS_DIR = "documents"
README_FILE = "README.txt"

# Cada tabla exportada va en `<tabla>.json` (la de `users`, en `account.json`), con
# todas sus columnas salvo estas. Lo que se omite es interno (ids de otros
# sistemas, rutas del almacén) o secreto, y el `user_id` repetido en cada fila.
EXPORTED_TABLES: dict[str, frozenset[str]] = {
    "users": frozenset({"supertokens_user_id"}),
    "companies": frozenset({"user_id"}),
    "applications": frozenset({"user_id"}),
    "application_status_changes": frozenset(),
    "interviews": frozenset(),
    "reminders": frozenset({"user_id"}),
    "documents": frozenset({"user_id", "storage_key"}),
    "profiles": frozenset({"user_id"}),
    "profile_entries": frozenset(),
    "profile_entry_bullets": frozenset(),
    "profile_skills": frozenset(),
    "profile_languages": frozenset(),
    "ai_proposals": frozenset({"user_id"}),
    "ai_consents": frozenset({"user_id"}),
    # Qué proveedor y modelo y desde cuándo; la clave nunca, ni cifrada ni sus
    # últimos caracteres (invariante 20).
    "ai_provider_keys": frozenset({"user_id", "ciphertext", "last4"}),
}

# Tablas con filas de la cuenta que no se exportan, y por qué.
EXCLUDED_TABLES: dict[str, str] = {
    "notification_deliveries": (
        "registro de los avisos que envió el sistema, no datos que aportara la persona"
    ),
    "user_limit_overrides": "configuración de quien administra la instalación",
}

# Caracteres que no valen en un nombre de fichero en algún sistema (Windows es el
# más estricto), más los de control.
_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def table_file(table: str) -> str:
    return ACCOUNT_FILE if table == "users" else f"{table}.json"


def document_path(document_id: uuid.UUID, name: str) -> str:
    """Ruta del PDF dentro del `.zip`: el id delante para que dos documentos con el
    mismo nombre no choquen, y el nombre visible para reconocerlo."""
    safe = _UNSAFE_FILENAME.sub("_", name).strip(" .") or "document"
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    return f"{DOCUMENTS_DIR}/{document_id}-{safe}"


def export_filename(exported_at: datetime) -> str:
    return f"applications-tracker-export-{exported_at:%Y-%m-%d}.zip"


def readme_text(exported_at: datetime, missing_documents: list[str]) -> str:
    """El README del `.zip`, en español y en inglés (la exportación no depende del
    idioma de la cuenta: la puede pedir quien administra la instalación). Va el
    último, para poder decir qué PDF faltaban al copiarlos."""
    files = ", ".join(table_file(table) for table in EXPORTED_TABLES)
    lines = [
        "Applications Tracker",
        f"{exported_at.isoformat()} · format_version {FORMAT_VERSION}",
        "",
        "ES · Todos los datos de tu cuenta.",
        f"- {ACCOUNT_FILE}: tu email, tus preferencias y la fecha de alta.",
        "- Un JSON por tipo de dato, con el nombre de su tabla. Los ids enlazan unos",
        "  con otros (application_id, company_id…); las fechas van en ISO 8601 (UTC).",
        f"- {DOCUMENTS_DIR}/: tus PDF (subidos y generados).",
        "- Nunca incluye tus claves de IA, solo qué proveedor y modelo usabas.",
        "",
        "EN · All the data in your account.",
        f"- {ACCOUNT_FILE}: your email, your preferences and the sign-up date.",
        "- One JSON per kind of data, named after its table. Ids link them together",
        "  (application_id, company_id…); dates are ISO 8601 (UTC).",
        f"- {DOCUMENTS_DIR}/: your PDFs (uploaded and generated).",
        "- It never includes your AI keys, only which provider and model you used.",
        "",
        f"Files: {files}.",
    ]
    if missing_documents:
        lines += [
            "",
            "ES · Estos PDF no estaban en el servidor al exportar (borrados mientras",
            "tanto, o perdidos): / EN · These PDFs were not on the server at export",
            "time (deleted meanwhile, or lost):",
            *(f"- {path}" for path in missing_documents),
        ]
    return "\n".join(lines) + "\n"


def to_json_value(value: Any) -> Any:
    """Un valor de columna en JSON: fechas en ISO 8601, ids como texto. Los bytes no
    tienen representación aquí: una columna binaria se omite a propósito o es un
    fallo (la única que existe es la clave cifrada)."""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes | bytearray | memoryview):
        raise TypeError("Una columna binaria no se exporta")
    return value
