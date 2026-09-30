"""Perfil profesional (F14, RF-100…106, v2 §4). Reglas puras, sin I/O.

El perfil es la materia prima de los CVs: lo que no está aquí no puede aparecer
en ningún CV generado ni, en F15, adaptado con IA.
"""

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
