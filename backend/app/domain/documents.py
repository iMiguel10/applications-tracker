"""Biblioteca de documentos (RF-90…94, ficheros §2). Reglas puras, sin I/O."""

import unicodedata
import uuid
from datetime import timedelta
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


class DocumentErrorCode(StrEnum):
    """Por qué falló un documento generado (F14). Es contrato: el frontend lo
    traduce (`errors.<code>`) y el mismo valor que el límite de almacenamiento
    (`LimitKey.STORAGE_BYTES`) dice lo mismo en los dos sitios."""

    RENDER_FAILED = "render_failed"
    STORAGE_LIMIT_REACHED = "storage_limit_reached"


NAME_MAX_LENGTH = 200
# Clave de un diseño (`templates/cv/<key>/`) y código de idioma de sus etiquetas.
TEMPLATE_MAX_LENGTH = 50


def storage_key(user_id: uuid.UUID, document_id: uuid.UUID) -> str:
    """Ruta del fichero relativa a la raíz del almacén (A23). La genera el servidor:
    el nombre original del fichero nunca llega al disco."""
    return f"users/{user_id}/documents/{document_id}.pdf"


def user_prefix(user_id: uuid.UUID) -> str:
    """Todo lo de una cuenta, para borrarlo con ella (RNF-41). Sin barra final:
    `delete_prefix` rechaza un segmento vacío, que es lo que evita que un id vacío
    (`users//`) acabe borrando `users` entero."""
    return f"users/{user_id}"


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
    # Sin la extensión: un nombre sin ningún carácter ASCII (`履歴書.pdf`) se
    # quedaría en `.pdf`, un fichero oculto sin nombre.
    stem, extension = filename[:-4], filename[-4:]
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    # Comillas y barras invertidas romperían el valor entrecomillado.
    ascii_stem = ascii_stem.replace('"', "").replace("\\", "").strip()
    ascii_name = f"{ascii_stem}{extension}" if ascii_stem else DEFAULT_NAME
    disposition = "attachment" if attachment else "inline"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


# Barrido de pendientes (segundo plano §3). Un CV se maqueta en un segundo: uno que
# sigue `pending` pasados 5 minutos perdió su trabajo (Valkey caído, worker
# reiniciado) y se reencola. Pasada una hora se da por fallido, para que un fallo
# que no es de la maquetación (el disco) no lo reencole para siempre.
PENDING_REQUEUE_AFTER = timedelta(minutes=5)
PENDING_GIVE_UP_AFTER = timedelta(hours=1)
PENDING_SWEEP_BATCH = 200

# Barrido de huérfanos (ficheros §5): no toca un fichero más reciente que esto.
# Entre escribir el fichero de una subida y confirmar su fila pasan milisegundos;
# sin margen, un barrido que coincidiera borraría una subida en curso.
ORPHAN_GRACE = timedelta(hours=1)
# Claves que se comprueban contra la BD en cada consulta.
ORPHAN_SWEEP_BATCH = 500
