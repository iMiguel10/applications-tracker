import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    """Solicitud a un puesto.

    F0: versión mínima (puesto + empresa en texto, sin usuario). Se rehace en F2
    con todas las columnas de docs/arquitectura/index.md §5.
    """

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    position_title: Mapped[str] = mapped_column(String(200))

    company_name: Mapped[str] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # clock_timestamp() y no now(): now() es la hora de inicio de la transacción y
        # daría el mismo valor a todas las filas escritas en ella (orden indeterminado).
        server_default=func.clock_timestamp(),
    )
