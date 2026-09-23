from abc import ABC, abstractmethod

from app.models.reminder import Reminder


class NotificationChannel(ABC):
    """Costura para avisar de un recordatorio por un medio concreto (RF-53).

    `ReminderService` depende solo de esta interfaz, nunca de una implementación:
    un canal nuevo (email, Telegram…) es una clase más, sin tocar el resto. En el
    MVP la única implementación es `InAppChannel`, que no envía nada.
    """

    @abstractmethod
    async def send(self, reminder: Reminder) -> None: ...
