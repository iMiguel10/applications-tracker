"""Valores cerrados de una entrevista (especificación §4, RF-40…42). Reglas puras."""

from enum import StrEnum


class InterviewType(StrEnum):
    SCREENING = "screening"
    TECHNICAL = "technical"
    HR = "hr"
    CULTURAL = "cultural"
    FINAL = "final"
    OTHER = "other"


class InterviewFormat(StrEnum):
    ONLINE = "online"
    ONSITE = "onsite"
    PHONE = "phone"


class InterviewOutcome(StrEnum):
    """Resultado de la entrevista (RF-41). `PENDING` es el valor por defecto."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
