"""Valores cerrados de un recordatorio (especificación §4, RF-50…53). Reglas puras."""

from enum import StrEnum


class ReminderChannel(StrEnum):
    """Dónde se ve el recordatorio: siempre `in_app` (RF-53). Los avisos por email
    no dependen de este valor: se activan en las preferencias de la cuenta
    (`notify_reminder_due`)."""

    IN_APP = "in_app"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DISMISSED = "dismissed"
