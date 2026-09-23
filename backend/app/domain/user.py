"""Preferencias de usuario (F8). Reglas puras, sin I/O."""

from enum import StrEnum


class Language(StrEnum):
    """Idioma de la interfaz. `null` en el usuario significa "sigue el navegador"."""

    ES = "es"
    EN = "en"


# RF-64: límites del umbral de "sin actividad" que el usuario puede fijar. El valor
# por defecto sigue viviendo en domain/dashboard.py (STALE_AFTER_DAYS).
MIN_STALE_AFTER_DAYS = 1
MAX_STALE_AFTER_DAYS = 90
