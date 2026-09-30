# Importar aquí cada modelo: es lo que los registra en Base.metadata, y
# migrations/env.py importa este paquete para que Alembic los vea.
from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.models.document import Document
from app.models.interview import Interview
from app.models.notification_delivery import NotificationDelivery
from app.models.profile import Profile
from app.models.profile_entry import ProfileEntry, ProfileEntryBullet
from app.models.reminder import Reminder
from app.models.user import User
from app.models.user_limit_override import UserLimitOverride

__all__ = [
    "Application",
    "ApplicationStatusChange",
    "Company",
    "Document",
    "Interview",
    "NotificationDelivery",
    "Profile",
    "ProfileEntry",
    "ProfileEntryBullet",
    "Reminder",
    "User",
    "UserLimitOverride",
]
