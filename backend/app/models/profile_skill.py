import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.profile import (
    LANGUAGE_NAME_MAX_LENGTH,
    SKILL_CATEGORY_MAX_LENGTH,
    SKILL_NAME_MAX_LENGTH,
    LanguageLevel,
    SkillLevel,
)


class ProfileSkill(Base):
    """Una habilidad del perfil (RF-102). Hija de `profiles`, sin `user_id`: el
    repository filtra con un join a `profiles.user_id` (invariante 1). En F15 la
    IA las prioriza y las referencia por id."""

    __tablename__ = "profile_skills"
    __table_args__ = (
        enum_check("level", SkillLevel, "level"),
        CheckConstraint("char_length(name) >= 1", name="name_not_empty"),
        # Sin repetir nombre, sin distinguir mayúsculas.
        Index(
            "uq_profile_skills_profile_id_name",
            "profile_id",
            func.lower(text("name")),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(SKILL_NAME_MAX_LENGTH))
    # Texto libre ("Lenguajes", "Herramientas"): el CV agrupa por ella.
    category: Mapped[str | None] = mapped_column(String(SKILL_CATEGORY_MAX_LENGTH))
    level: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)


class ProfileLanguage(Base):
    """Un idioma del perfil con su nivel (RF-102)."""

    __tablename__ = "profile_languages"
    __table_args__ = (
        enum_check("level", LanguageLevel, "level"),
        CheckConstraint("char_length(language) >= 1", name="language_not_empty"),
        Index(
            "uq_profile_languages_profile_id_language",
            "profile_id",
            func.lower(text("language")),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE")
    )
    # El nombre tal como se quiere mostrar ("Inglés", "English").
    language: Mapped[str] = mapped_column(String(LANGUAGE_NAME_MAX_LENGTH))
    level: Mapped[str] = mapped_column(String(10))
    position: Mapped[int] = mapped_column(Integer)
