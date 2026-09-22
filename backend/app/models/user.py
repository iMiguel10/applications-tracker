import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Enlace con el usuario de SuperTokens (arquitectura §4, decisión A12).

    No copia datos de identidad (email, nombre): se piden a SuperTokens cuando
    hacen falta. Existe para las FKs y el ON DELETE CASCADE de los datos propios.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    supertokens_user_id: Mapped[str] = mapped_column(String(128), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
