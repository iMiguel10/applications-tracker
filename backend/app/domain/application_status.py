"""Estados de una solicitud y su máquina de transiciones (especificación §6).

Reglas puras, sin I/O: la usan services (para validar) y schemas (para exponer
`allowed_transitions` en la API, decisión A8).
"""

from collections.abc import Mapping
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

# Tabla completa de transiciones permitidas (especificación §6). El orden de cada
# tupla es el que se ofrece en el desplegable del frontend: no es alfabético, sigue
# el orden "natural" del proceso (avanzar antes que descartar o retirarse).
ALLOWED_TRANSITIONS: Mapping[ApplicationStatus, tuple[ApplicationStatus, ...]] = {
    ApplicationStatus.SAVED: (
        ApplicationStatus.APPLIED,
        ApplicationStatus.WITHDRAWN,
    ),
    ApplicationStatus.APPLIED: (
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ),
    ApplicationStatus.SCREENING: (
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ),
    ApplicationStatus.INTERVIEWING: (
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ),
    ApplicationStatus.OFFER: (
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ),
    # Estados finales (regla 3 de la especificación): sin salida.
    ApplicationStatus.ACCEPTED: (),
    ApplicationStatus.REJECTED: (),
    ApplicationStatus.WITHDRAWN: (),
}


def allowed_transitions(
    from_status: ApplicationStatus,
) -> tuple[ApplicationStatus, ...]:
    """Transiciones disponibles desde `from_status`, en el orden a mostrar (A8)."""
    return ALLOWED_TRANSITIONS[from_status]


def is_transition_allowed(
    from_status: ApplicationStatus, to_status: ApplicationStatus
) -> bool:
    return to_status in ALLOWED_TRANSITIONS[from_status]
