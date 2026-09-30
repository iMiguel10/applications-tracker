"""Enlaces de baja de los avisos por email (RF-85, segundo plano §5). Reglas puras:
el secreto llega como parámetro.

El token es `<usuario>.<tipo>.<firma>`: una firma HMAC de `(usuario, tipo)`. No se
guarda en la BD y no caduca, porque un enlace de baja de hace un año tiene que
seguir funcionando. Sirve para un usuario y un tipo de aviso, nada más.
"""

import base64
import hashlib
import hmac
import uuid

from app.domain.notifications import NotificationKind

# La preferencia que desactiva cada tipo de aviso (RF-84).
PREFERENCE_FOR_KIND: dict[NotificationKind, str] = {
    NotificationKind.REMINDER_DUE: "notify_reminder_due",
    NotificationKind.INTERVIEW_UPCOMING: "notify_interview",
    NotificationKind.WEEKLY_DIGEST: "notify_weekly_digest",
    NotificationKind.STALE_APPLICATION: "notify_stale",
}

# La clave se deriva del secreto de la instalación con un propósito propio: si
# otra función firmara algo con APP_SECRET, sus firmas no valdrían aquí.
_PURPOSE = b"notification-unsubscribe"


def _signature(payload: str, secret: str) -> str:
    key = hmac.new(secret.encode(), _PURPOSE, hashlib.sha256).digest()
    digest = hmac.new(key, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def unsubscribe_token(user_id: uuid.UUID, kind: NotificationKind, secret: str) -> str:
    payload = f"{user_id.hex}.{kind.value}"
    return f"{payload}.{_signature(payload, secret)}"


def verify_unsubscribe_token(
    token: str, secret: str
) -> tuple[uuid.UUID, NotificationKind] | None:
    """El usuario y el tipo de un token con firma válida; None si no lo es."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    user_hex, kind_value, signature = parts
    payload = f"{user_hex}.{kind_value}"
    # Comparación en tiempo constante: no deja adivinar la firma byte a byte.
    if not hmac.compare_digest(signature, _signature(payload, secret)):
        return None
    try:
        return uuid.UUID(hex=user_hex), NotificationKind(kind_value)
    except ValueError:
        return None
