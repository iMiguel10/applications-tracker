"""Notificaciones por email (F12, RF-80…87). Reglas puras, sin I/O.

La parte difícil es "nunca dos veces" (RF-87): cada envío pasa por una entrega
(`notification_deliveries`) que se reclama y se confirma antes de hablar con el
SMTP, y cuyo estado dice si se puede reintentar (segundo plano §4).
"""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum


class NotificationKind(StrEnum):
    REMINDER_DUE = "reminder_due"
    INTERVIEW_UPCOMING = "interview_upcoming"
    WEEKLY_DIGEST = "weekly_digest"
    STALE_APPLICATION = "stale_application"


class DeliveryChannel(StrEnum):
    """Por dónde sale un aviso. Solo existe el email; va en la entrega, y en su clave
    única, para que un mismo motivo avisado por dos canales sean dos entregas y no
    se bloqueen entre sí (decisión 0012)."""

    EMAIL = "email"


class DeliveryStatus(StrEnum):
    # Reclamada y confirmada; el envío está en marcha (o el proceso murió a mitad).
    CLAIMED = "claimed"
    # El servidor SMTP aceptó el mensaje.
    SENT = "sent"
    # Falló ANTES de entregarlo: con seguridad no salió, se puede reintentar.
    FAILED = "failed"
    # No se sabe si salió: nunca se reintenta. Perder un email es aceptable;
    # duplicarlo, no (RF-87).
    UNKNOWN = "unknown"


# Intentos de envío de una entrega, el primero incluido.
MAX_DELIVERY_ATTEMPTS = 3

# Espera antes del siguiente intento, según los que ya se hicieron (espera
# creciente, segundo plano §4). Tras el último no hay espera: se da por fallida.
_RETRY_DELAYS = (timedelta(minutes=5), timedelta(minutes=30))


def next_attempt_at(attempts: int, failed_at: datetime) -> datetime | None:
    """Cuándo se puede volver a intentar una entrega que ha fallado `attempts`
    veces. None si ya agotó los intentos."""
    if attempts >= MAX_DELIVERY_ATTEMPTS:
        return None
    return failed_at + _RETRY_DELAYS[attempts - 1]


# Un reclamo que sigue en `claimed` pasado este tiempo es de un proceso que murió
# a mitad: pasa a `unknown`, nunca a reenviarse. Muy por encima del timeout del
# trabajo de envío (30 s), para no tomar por abandonado uno que espera en la cola.
ABANDONED_CLAIM_AFTER = timedelta(minutes=10)

# RF-80: antelación del aviso de recordatorio, en horas. 0 = al vencer (por
# defecto): la fecha del recordatorio es el momento del aviso, salvo que el usuario
# lo use como fecha límite y quiera saberlo antes.
DEFAULT_REMINDER_NOTICE_HOURS = 0
MIN_REMINDER_NOTICE_HOURS = 0
MAX_REMINDER_NOTICE_HOURS = 168

# RF-81: antelación del aviso de entrevista, en horas.
DEFAULT_INTERVIEW_NOTICE_HOURS = 24
MIN_INTERVIEW_NOTICE_HOURS = 1
MAX_INTERVIEW_NOTICE_HOURS = 168

# Barridos: cuántos avisos reclama como mucho una pasada. Lo que no cabe entra en
# la siguiente (segundo plano §3).
SWEEP_MAX_CLAIMS = 200

# RF-80: solo se avisa si el momento del aviso (la fecha menos la antelación) cayó
# en las últimas 24 h. Sin esta ventana, el día que se activa el canal saldría un
# email por cada recordatorio vencido desde que el usuario empezó a usar la
# aplicación (segundo plano §3, B7).
REMINDER_DUE_WINDOW = timedelta(hours=24)
REMINDER_KEY_PREFIX = "reminder:"


def reminder_due_key(reminder_id: uuid.UUID) -> str:
    """El motivo de un aviso de recordatorio vencido: uno por recordatorio, para
    siempre (segundo plano §4)."""
    return f"{REMINDER_KEY_PREFIX}{reminder_id}"


def reminder_id_from_key(dedupe_key: str) -> uuid.UUID | None:
    if not dedupe_key.startswith(REMINDER_KEY_PREFIX):
        return None
    try:
        return uuid.UUID(dedupe_key.removeprefix(REMINDER_KEY_PREFIX))
    except ValueError:
        return None


INTERVIEW_KEY_PREFIX = "interview:"


def interview_key(interview_id: uuid.UUID, scheduled_at: datetime) -> str:
    """El motivo de un aviso de entrevista: la entrevista **y su hora**, en
    segundos desde 1970 (UTC). Si el usuario la mueve, el aviso nuevo es otro motivo
    y no queda bloqueado por el de la hora antigua (segundo plano §4, B8). Los
    segundos, y no el texto ISO, porque la consulta del barrido construye la misma
    clave en SQL y un número no depende del formato de fecha de nadie."""
    return f"{INTERVIEW_KEY_PREFIX}{interview_id}:{int(scheduled_at.timestamp())}"


def interview_from_key(dedupe_key: str) -> tuple[uuid.UUID, int] | None:
    """La entrevista y su hora (segundos UTC) de una clave; None si no es de una."""
    if not dedupe_key.startswith(INTERVIEW_KEY_PREFIX):
        return None
    interview_id, _, seconds = dedupe_key.removeprefix(INTERVIEW_KEY_PREFIX).partition(
        ":"
    )
    try:
        return uuid.UUID(interview_id), int(seconds)
    except ValueError:
        return None


STALE_KEY_PREFIX = "stale:"


def stale_key(application_id: uuid.UUID, last_activity_at: datetime) -> str:
    """El motivo de un aviso de solicitud sin actividad: la solicitud **y el
    momento de su última actividad**, en segundos UTC. Un aviso por periodo de
    inactividad: si la solicitud se vuelve a mover y a quedarse quieta, es otro
    motivo (RF-83, segundo plano §4)."""
    return f"{STALE_KEY_PREFIX}{application_id}:{int(last_activity_at.timestamp())}"


def stale_from_key(dedupe_key: str) -> tuple[uuid.UUID, int] | None:
    """La solicitud y su última actividad (segundos UTC); None si no es una clave de
    este tipo."""
    if not dedupe_key.startswith(STALE_KEY_PREFIX):
        return None
    application_id, _, seconds = dedupe_key.removeprefix(STALE_KEY_PREFIX).partition(
        ":"
    )
    try:
        return uuid.UUID(application_id), int(seconds)
    except ValueError:
        return None
