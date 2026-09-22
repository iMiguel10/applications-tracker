"""Estados de una solicitud (especificación §6). Reglas puras, sin I/O.

F2 solo define los estados y con cuáles se puede crear una solicitud. La tabla de
transiciones y allowed_transitions() llegan en F3.
"""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# Regla 5 de la especificación: una solicitud nace guardada o ya enviada.
INITIAL_STATUSES = frozenset({ApplicationStatus.SAVED, ApplicationStatus.APPLIED})

# Estados en los que la solicitud puede no tener fecha de envío: nunca se envió
# (saved) o se retiró antes de enviarla (withdrawn desde saved). En el resto,
# applied_at es obligatoria (CHECK en la BD).
STATUSES_WITHOUT_APPLIED_AT = frozenset(
    {ApplicationStatus.SAVED, ApplicationStatus.WITHDRAWN}
)
