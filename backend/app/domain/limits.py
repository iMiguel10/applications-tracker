"""Límites por usuario (especificación §10, RF-140…144). Reglas puras, sin I/O.

Cada límite tiene un valor global (configuración, `LIMIT_<CLAVE>`) y puede tener
una excepción por usuario (`user_limit_overrides`). El consumo no se guarda en
contadores: se calcula sobre las tablas reales (límites y abuso §1).
"""

from dataclasses import dataclass
from enum import StrEnum


class LimitKey(StrEnum):
    APPLICATIONS = "applications"
    COMPANIES = "companies"
    # Todos los estados: si solo contaran los pendientes, crear, completar y
    # repetir haría crecer la tabla sin tope (decisión 0011).
    REMINDERS = "reminders"
    DOCUMENTS = "documents"
    # Suma de los tamaños de los documentos, archivados incluidos (siguen en disco).
    STORAGE_BYTES = "storage_bytes"
    # Usos gratuitos de IA con la clave de la plataforma, por tarea (decisión 0017):
    # lo facturado más lo que está en curso (ia.md §6). No se renuevan.
    AI_CV_PROPOSALS = "ai_cv_proposals"
    AI_COVER_LETTER_PROPOSALS = "ai_cover_letter_proposals"


class LimitUnit(StrEnum):
    """Cómo se muestra el consumo: la interfaz formatea los bytes."""

    COUNT = "count"
    BYTES = "bytes"


@dataclass(frozen=True)
class LimitRule:
    # Código estable del error al alcanzarlo. Es anterior a la clave (existe desde
    # el MVP).
    error_code: str
    # Si el consumo vuelve a cero cada cierto tiempo. Ninguno lo hace en la v2: los
    # usos gratuitos de IA (F15) tampoco se renuevan, y la interfaz lo dice.
    renews: bool = False
    # Si una cuenta puede quedar "sin límite" con una excepción. Por defecto NO: los
    # límites que protegen un recurso con coste (almacenamiento, IA) tienen tope
    # siempre, decisión del usuario en F11. Solo se permite donde pasarse no cuesta
    # nada más que filas.
    allows_unlimited: bool = False
    unit: LimitUnit = LimitUnit.COUNT


LIMIT_RULES: dict[LimitKey, LimitRule] = {
    LimitKey.APPLICATIONS: LimitRule(
        error_code="applications_limit_reached", allows_unlimited=True
    ),
    LimitKey.COMPANIES: LimitRule(
        error_code="companies_limit_reached", allows_unlimited=True
    ),
    LimitKey.REMINDERS: LimitRule(
        error_code="reminders_limit_reached", allows_unlimited=True
    ),
    # Cada documento ocupa disco, pero eso ya lo acota el almacenamiento: contar
    # documentos solo cuesta filas.
    LimitKey.DOCUMENTS: LimitRule(
        error_code="documents_limit_reached", allows_unlimited=True
    ),
    LimitKey.STORAGE_BYTES: LimitRule(
        error_code="storage_limit_reached", unit=LimitUnit.BYTES
    ),
    # Cuestan dinero de la plataforma: nunca "sin límite" (F11). Mismo código para
    # las dos: la interfaz explica cómo seguir con una clave propia (RF-156).
    LimitKey.AI_CV_PROPOSALS: LimitRule(error_code="ai_free_quota_exhausted"),
    LimitKey.AI_COVER_LETTER_PROPOSALS: LimitRule(error_code="ai_free_quota_exhausted"),
}


def keys_allowing_unlimited() -> list[LimitKey]:
    return [key for key, rule in LIMIT_RULES.items() if rule.allows_unlimited]


# RF-144: a partir de aquí se avisa antes de llegar al tope. Lo aplica el frontend
# con los números de GET /me/usage.
WARNING_RATIO = 0.8


def remaining(used: int, limit: int | None) -> int | None:
    """Lo que queda, nunca negativo: una excepción rebajada por debajo de lo ya
    creado no borra nada, solo impide crear más. None si no hay límite."""
    return None if limit is None else max(limit - used, 0)
