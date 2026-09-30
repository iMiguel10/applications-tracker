"""Biblioteca de documentos (RF-90…94, ficheros §2). Reglas puras, sin I/O."""

import uuid
from enum import StrEnum


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
