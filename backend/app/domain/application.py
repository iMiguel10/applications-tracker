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


class Currency(StrEnum):
    """Monedas disponibles para el rango salarial (F8: desplegable cerrado, no
    texto libre). Ampliar esta lista es un cambio pequeño y acotado."""

    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    CHF = "CHF"


DEFAULT_CURRENCY = Currency.EUR

# Límite de la especificación §10. Los de cantidad por usuario (solicitudes,
# empresas) viven en domain/limits.py y la configuración.
MAX_NOTES_LENGTH = 5_000
