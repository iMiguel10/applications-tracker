"""Valores cerrados de los campos de una solicitud. Reglas puras, sin I/O."""

from enum import StrEnum


class WorkMode(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class ApplicationSource(StrEnum):
    """Dónde se encontró la oferta."""

    LINKEDIN = "linkedin"
    INFOJOBS = "infojobs"
    INDEED = "indeed"
    COMPANY_WEBSITE = "company_website"
    REFERRAL = "referral"
    RECRUITER = "recruiter"
    OTHER = "other"


class ApplicationOrigin(StrEnum):
    """Cómo entró la solicitud en el sistema (RF-26). Costura para importaciones:
    en el MVP solo existe el registro manual."""

    MANUAL = "manual"


DEFAULT_CURRENCY = "EUR"

# Límites de la especificación §10.
MAX_APPLICATIONS_PER_USER = 5_000
MAX_COMPANIES_PER_USER = 2_000
MAX_NOTES_LENGTH = 5_000
