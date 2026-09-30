"""Biblioteca de documentos (RF-90…94, ficheros §2). Reglas puras, sin I/O."""

import unicodedata
import uuid
from enum import StrEnum
from urllib.parse import quote


class DocumentKind(StrEnum):
    CV = "cv"
    COVER_LETTER = "cover_letter"


class DocumentOrigin(StrEnum):
    """RF-91: de dónde sale. Los generados (F14) y los adaptados con IA (F15) llegan
    en sus fases; el CHECK los admite desde ya para no rehacerlo."""

    UPLOADED = "uploaded"
    GENERATED = "generated"
    AI_TAILORED = "ai_tailored"


class DocumentStatus(StrEnum):
    """Un subido nace `ready`. Uno generado nace `pending` y el `worker` lo pasa a
    `ready` o `failed` (A35)."""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


NAME_MAX_LENGTH = 200


def storage_key(user_id: uuid.UUID, document_id: uuid.UUID) -> str:
    """Ruta del fichero relativa a la raíz del almacén (A23). La genera el servidor:
    el nombre original del fichero nunca llega al disco."""
    return f"users/{user_id}/documents/{document_id}.pdf"


def user_prefix(user_id: uuid.UUID) -> str:
    """Todo lo de una cuenta, para borrarlo con ella (RNF-41)."""
    return f"users/{user_id}/"


# Los primeros bytes de todo PDF (ficheros §2, paso 3). La extensión no dice nada.
PDF_SIGNATURE = b"%PDF-"
# Abrir el PDF para contar páginas, con un tope: hay PDFs hechos para colgar a
# quien los procesa (ficheros §2).
PDF_INSPECT_TIMEOUT_SECONDS = 5.0
DEFAULT_NAME = "documento.pdf"

# Caracteres de control (incluidos saltos de línea y tabuladores) y los invisibles
# de formato Unicode (direccionales, de anchura cero): con ellos un nombre puede
# aparentar otra extensión ("cv\u202efdp.exe").
_UNSAFE_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}


def sanitize_name(raw: str | None) -> str:
    """Nombre visible a partir del que envía el cliente (A23). Solo se muestra:
    nunca llega al disco. Quita la ruta que mandan algunos navegadores antiguos
    (`C:\\fakepath\\cv.pdf`), los caracteres de control e invisibles y los
    espacios repetidos, y lo recorta sin partir la extensión."""
    name = unicodedata.normalize("NFC", raw or "")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        " " if unicodedata.category(char) in _UNSAFE_CATEGORIES else char
        for char in name
    )
    name = " ".join(name.split())
    if not name or name in {".", ".."}:
        return DEFAULT_NAME
    if len(name) > NAME_MAX_LENGTH:
        stem, dot, extension = name.rpartition(".")
        if dot and 0 < len(extension) <= 10:
            name = (
                stem[: NAME_MAX_LENGTH - len(extension) - 1].rstrip() + "." + extension
            )
        else:
            name = name[:NAME_MAX_LENGTH].rstrip()
    return name


def download_name(name: str) -> str:
    """Nombre del fichero al descargarlo: el visible, siempre acabado en `.pdf` (se
    sirve siempre como PDF, diga lo que diga el nombre)."""
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


def content_disposition(name: str, *, attachment: bool) -> str:
    """`Content-Disposition` con el nombre del documento (ficheros §4, D8).

    Una cabecera HTTP solo admite ASCII: se envía `filename` en ASCII (con las
    tildes quitadas por NFKD: codificar a ASCII sin más quita la letra entera,
    `currculum`) **y** `filename*` en UTF-8 (RFC 5987), que prefieren los
    navegadores modernos."""
    filename = download_name(name)
    ascii_name = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    )
    # Comillas y barras invertidas romperían el valor entrecomillado.
    ascii_name = ascii_name.replace('"', "").replace("\\", "").strip() or DEFAULT_NAME
    disposition = "attachment" if attachment else "inline"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )
