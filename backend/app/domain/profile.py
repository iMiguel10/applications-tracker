"""Perfil profesional (F14, RF-100…106, v2 §4). Reglas puras, sin I/O.

El perfil es la materia prima de los CVs: lo que no está aquí no puede aparecer
en ningún CV generado ni, en F15, adaptado con IA.
"""

from enum import StrEnum
from urllib.parse import urlsplit

FULL_NAME_MAX_LENGTH = 200
HEADLINE_MAX_LENGTH = 200
CONTACT_EMAIL_MAX_LENGTH = 254
PHONE_MAX_LENGTH = 50
LOCATION_MAX_LENGTH = 200
SUMMARY_MAX_LENGTH = 2_000

# Enlaces del CV (web, LinkedIn, GitHub…).
MAX_LINKS = 10
LINK_LABEL_MAX_LENGTH = 50
LINK_URL_MAX_LENGTH = 500
_LINK_SCHEMES = frozenset({"http", "https"})


def is_safe_link(url: str) -> bool:
    """Un enlace del perfil solo puede ser http(s) con un host.

    Se pinta como `<a href>` en la interfaz y en el PDF: `javascript:` o `data:`
    serían un XSS en la aplicación, y un `file:` o una ruta relativa, un enlace
    roto en el CV. No se comprueba que el host exista."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in _LINK_SCHEMES and bool(parts.hostname)


# --- Entradas del perfil (RF-101, RF-102) -------------------------------------


class EntryKind(StrEnum):
    """Secciones del perfil con la misma forma: título, organización, fechas,
    descripción y logros (A26)."""

    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECT = "project"
    CERTIFICATION = "certification"


ENTRY_TITLE_MAX_LENGTH = 200
ENTRY_ORGANIZATION_MAX_LENGTH = 200
ENTRY_LOCATION_MAX_LENGTH = 200
ENTRY_DESCRIPTION_MAX_LENGTH = 2_000
BULLET_MAX_LENGTH = 500
MAX_BULLETS_PER_ENTRY = 20

# Topes de tamaño del perfil (especificación §10): acotan el PDF y, en F15, la
# entrada a la IA. No son cuotas de la cuenta: no se ven en el uso ni admiten
# excepciones por usuario.
MAX_ENTRIES: dict[EntryKind, int] = {
    EntryKind.EXPERIENCE: 50,
    EntryKind.EDUCATION: 30,
    EntryKind.PROJECT: 30,
    EntryKind.CERTIFICATION: 30,
}


# --- Habilidades e idiomas (RF-102) -------------------------------------------


class SkillLevel(StrEnum):
    """Nivel opcional de una habilidad."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LanguageLevel(StrEnum):
    """Marco Común Europeo de Referencia, más nativo."""

    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"
    C2 = "c2"
    NATIVE = "native"


SKILL_NAME_MAX_LENGTH = 100
SKILL_CATEGORY_MAX_LENGTH = 100
LANGUAGE_NAME_MAX_LENGTH = 100
# Especificación §10: 100 habilidades y 30 de cada otra sección.
MAX_SKILLS = 100
MAX_LANGUAGES = 30


def name_key(name: str) -> str:
    """Clave de unicidad de un nombre: sin distinguir mayúsculas, como el índice
    `lower(name)` de la BD."""
    return name.lower()
