"""Preferencias de usuario (F8, F11). Reglas puras, sin I/O de la aplicación."""

import zoneinfo
from enum import StrEnum
from functools import cache


class Language(StrEnum):
    """Idioma de la interfaz. `null` en el usuario significa "sigue el navegador"."""

    ES = "es"
    EN = "en"


DEFAULT_LANGUAGE = Language.ES


def language_from_accept_language(header: str | None) -> Language | None:
    """El primer idioma soportado de una cabecera `Accept-Language`, respetando su
    orden de preferencia (`q`). None si no hay ninguno soportado.

    Sirve para los emails que se piden sin sesión (recuperar la contraseña): si la
    cuenta no tiene idioma fijado, se usa el del navegador que lo pidió, igual que
    hace la interfaz.
    """
    if not header:
        return None
    candidates: list[tuple[float, int, str]] = []
    for position, part in enumerate(header.split(",")):
        tag, _, params = part.strip().partition(";")
        quality = 1.0
        params = params.strip()
        if params.startswith("q="):
            try:
                quality = float(params[2:])
            except ValueError:
                continue
        primary = tag.strip().split("-")[0].lower()
        if quality > 0 and primary:
            candidates.append((-quality, position, primary))
    for _, _, primary in sorted(candidates):
        if primary in Language._value2member_map_:
            return Language(primary)
    return None


# Nombre IANA ("Europe/Madrid"), nunca un desfase ("+02:00"): el desfase cambia
# dos veces al año con el horario de verano (A39).
MAX_TIMEZONE_LENGTH = 64


@cache
def _known_timezones() -> frozenset[str]:
    # La base de datos de zonas del sistema (tzdata de la imagen): datos estáticos,
    # se leen una vez.
    return frozenset(zoneinfo.available_timezones())


def is_valid_timezone(name: str) -> bool:
    return name in _known_timezones()


# RF-64: límites del umbral de "sin actividad" que el usuario puede fijar. El valor
# por defecto sigue viviendo en domain/dashboard.py (STALE_AFTER_DAYS).
MIN_STALE_AFTER_DAYS = 1
MAX_STALE_AFTER_DAYS = 90
