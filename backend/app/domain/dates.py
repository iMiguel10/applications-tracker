"""Fechas en la zona horaria y el idioma del usuario, para los emails (RF-07,
RF-86). Reglas puras, sin I/O de la aplicación.

Solo hay dos idiomas: una tabla de nombres basta y evita una dependencia como
Babel. Si llegan más idiomas, es el momento de cambiarla.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.user import Language

_WEEKDAYS = {
    Language.ES: (
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
    ),
    Language.EN: (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ),
}
_MONTHS = {
    Language.ES: (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ),
    Language.EN: (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}


def format_local_datetime(
    instant: datetime, timezone: str | None, language: Language
) -> str:
    """ "lunes, 5 de octubre de 2026, 09:30" / "Monday, October 5, 2026, 09:30".

    Un instante en UTC se pasa a la zona del usuario (nombre IANA, A39). Sin zona,
    se usa UTC y se dice, para que nadie lea la hora como si fuera la suya.
    """
    local = instant.astimezone(ZoneInfo(timezone or "UTC"))
    weekday = _WEEKDAYS[language][local.weekday()]
    month = _MONTHS[language][local.month - 1]
    time = f"{local:%H:%M}"
    if language == Language.ES:
        text = f"{weekday}, {local.day} de {month} de {local.year}, {time}"
    else:
        text = f"{weekday}, {month} {local.day}, {local.year}, {time}"
    return text if timezone else f"{text} (UTC)"
