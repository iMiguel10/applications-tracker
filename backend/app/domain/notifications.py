"""Notificaciones por email (F12, RF-80…87). Reglas puras, sin I/O.

La parte difícil es "nunca dos veces" (RF-87): cada envío pasa por una entrega
(`notification_deliveries`) que se reclama y se confirma antes de hablar con el
SMTP, y cuyo estado dice si se puede reintentar (segundo plano §4).
"""

from datetime import datetime, timedelta
from enum import StrEnum


class NotificationKind(StrEnum):
    REMINDER_DUE = "reminder_due"
    INTERVIEW_UPCOMING = "interview_upcoming"
    WEEKLY_DIGEST = "weekly_digest"
    STALE_APPLICATION = "stale_application"


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

# RF-81: antelación del aviso de entrevista, en horas.
DEFAULT_INTERVIEW_NOTICE_HOURS = 24
MIN_INTERVIEW_NOTICE_HOURS = 1
MAX_INTERVIEW_NOTICE_HOURS = 168
