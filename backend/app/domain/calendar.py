"""Calendario de entrevistas y recordatorios (RF-130…134). Reglas puras, sin I/O."""

from datetime import timedelta
from enum import StrEnum


class CalendarEventKind(StrEnum):
    INTERVIEW = "interview"
    REMINDER = "reminder"


# El rango más largo que se pide de una vez. La vista de mes pinta 6 semanas
# (42 días) y sobra margen; un tope evita que una petición recorra años.
MAX_CALENDAR_RANGE = timedelta(days=62)
