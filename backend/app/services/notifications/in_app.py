from app.models.reminder import Reminder
from app.services.notifications.base import NotificationChannel


class InAppChannel(NotificationChannel):
    """Único canal del MVP (RF-53): el recordatorio se ve al consultar la API, así
    que "enviarlo" no hace nada. No hay trabajo en segundo plano que lo dispare.

    A propósito nunca toca `sent_at`: esa columna es para canales que sí entregan
    algo fuera de la aplicación.
    """

    async def send(self, reminder: Reminder) -> None:
        return None
