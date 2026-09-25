"""Valores cerrados de un recordatorio (especificación §4, RF-50…53). Reglas puras."""

from enum import StrEnum


class ReminderChannel(StrEnum):
    """Por dónde se avisa. En el MVP solo existe `IN_APP` (RF-53): es la costura
    para futuros canales (email, Telegram…), que llegarían como una implementación
    nueva de `NotificationChannel` más este valor."""

    IN_APP = "in_app"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DISMISSED = "dismissed"
