import uuid
from datetime import date
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.profile import (
    BULLET_MAX_LENGTH,
    CONTACT_EMAIL_MAX_LENGTH,
    ENTRY_DESCRIPTION_MAX_LENGTH,
    LANGUAGE_NAME_MAX_LENGTH,
    LINK_LABEL_MAX_LENGTH,
    LINK_URL_MAX_LENGTH,
    MAX_BULLETS_PER_ENTRY,
    MAX_ENTRIES,
    MAX_LANGUAGES,
    MAX_LINKS,
    MAX_SKILLS,
    PHONE_MAX_LENGTH,
    SKILL_CATEGORY_MAX_LENGTH,
    SKILL_NAME_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
    EntryKind,
    LanguageLevel,
    SkillLevel,
    is_safe_link,
)
from app.schemas.common import OptionalShortText, RequiredName, empty_to_none


def _safe_link(value: str) -> str:
    if not is_safe_link(value):
        raise ValueError("Only http and https links are allowed")
    return value


LinkUrl = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=LINK_URL_MAX_LENGTH
    ),
    AfterValidator(_safe_link),
]
LinkLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=LINK_LABEL_MAX_LENGTH
    ),
]
OptionalContactEmail = Annotated[
    Annotated[EmailStr, Field(max_length=CONTACT_EMAIL_MAX_LENGTH)] | None,
    BeforeValidator(empty_to_none),
]
# El teléfono se escribe como se quiera mostrar ("+34 600 00 00 00"): solo se
# limitan los caracteres, no el formato.
OptionalPhone = Annotated[
    Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            max_length=PHONE_MAX_LENGTH,
            pattern=r"^[0-9+()./\- ]+$",
        ),
    ]
    | None,
    BeforeValidator(empty_to_none),
]
OptionalSummary = Annotated[
    Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=SUMMARY_MAX_LENGTH)
    ]
    | None,
    BeforeValidator(empty_to_none),
]


class ProfileLink(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: LinkLabel = Field(examples=["LinkedIn"])
    url: LinkUrl = Field(
        description="Solo `http` o `https`.",
        examples=["https://www.linkedin.com/in/ana"],
    )


class ProfileBasics(BaseModel):
    """Datos de contacto y resumen del CV (RF-100). Son los del CV, no los de la
    cuenta: el email de contacto puede ser otro."""

    full_name: OptionalShortText = Field(default=None, examples=["Ana García"])
    headline: OptionalShortText = Field(
        default=None,
        description="Titular bajo el nombre.",
        examples=["Desarrolladora backend"],
    )
    contact_email: OptionalContactEmail = Field(
        default=None, examples=["ana@example.com"]
    )
    phone: OptionalPhone = Field(default=None, examples=["+34 600 000 000"])
    location: OptionalShortText = Field(default=None, examples=["Madrid, España"])
    links: list[ProfileLink] = Field(default_factory=list, max_length=MAX_LINKS)
    summary: OptionalSummary = Field(default=None, description="Resumen profesional.")


class ProfileUpdate(ProfileBasics):
    """Sustituye los datos básicos enteros (PUT): un campo que no se envía queda
    vacío."""


class ProfileRead(ProfileBasics):
    model_config = ConfigDict(from_attributes=True)


# --- Entradas del perfil (RF-101, RF-102) -------------------------------------

BulletText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=BULLET_MAX_LENGTH
    ),
]
OptionalDescription = Annotated[
    Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=ENTRY_DESCRIPTION_MAX_LENGTH
        ),
    ]
    | None,
    BeforeValidator(empty_to_none),
]


class BulletWrite(BaseModel):
    """Un logro. Con `id`, el existente con ese id (conserva su identidad para
    F15); sin él, uno nuevo."""

    id: uuid.UUID | None = None
    text: BulletText = Field(examples=["Reduje a la mitad el tiempo de despliegue"])


class BulletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str


class EntryFields(BaseModel):
    title: RequiredName = Field(
        description="Puesto, título académico, nombre del proyecto o de la "
        "certificación.",
        examples=["Desarrolladora backend"],
    )
    organization: OptionalShortText = Field(default=None, examples=["Acme"])
    location: OptionalShortText = Field(default=None, examples=["Madrid"])
    start_date: date | None = Field(
        default=None,
        description="Un CV muestra mes y año; la aplicación web envía el día 1.",
    )
    end_date: date | None = None
    is_current: bool = Field(
        default=False, description="Sigue en curso: sin fecha de fin."
    )
    description: OptionalDescription = None
    bullets: list[BulletWrite] = Field(
        default_factory=list,
        max_length=MAX_BULLETS_PER_ENTRY,
        description="Logros, en el orden en que se muestran.",
    )

    @model_validator(mode="after")
    def _dates_make_sense(self) -> Self:
        if self.is_current and self.end_date is not None:
            raise ValueError("An entry in progress has no end date")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("The end date is before the start date")
        return self


class EntryCreate(EntryFields):
    kind: EntryKind


class EntryUpdate(EntryFields):
    """Sustituye la entrada entera. La sección (`kind`) no cambia."""


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: EntryKind
    title: str
    organization: str | None
    location: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str | None
    bullets: list[BulletRead]


class EntryOrder(BaseModel):
    """El orden nuevo de una sección: exactamente todos sus ids."""

    kind: EntryKind
    entry_ids: list[uuid.UUID] = Field(max_length=max(MAX_ENTRIES.values()))


# --- Habilidades e idiomas (RF-102) -------------------------------------------

SkillName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=SKILL_NAME_MAX_LENGTH
    ),
]
OptionalCategory = Annotated[
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, max_length=SKILL_CATEGORY_MAX_LENGTH),
    ]
    | None,
    BeforeValidator(empty_to_none),
]
LanguageName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=LANGUAGE_NAME_MAX_LENGTH
    ),
]


class SkillWrite(BaseModel):
    """Con `id`, la habilidad existente con ese id (conserva su identidad para
    F15); sin él, una nueva."""

    id: uuid.UUID | None = None
    name: SkillName = Field(examples=["PostgreSQL"])
    category: OptionalCategory = Field(default=None, examples=["Bases de datos"])
    level: SkillLevel | None = None


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str | None
    level: SkillLevel | None


class SkillsUpdate(BaseModel):
    """La lista entera, en el orden en que se muestra."""

    skills: list[SkillWrite] = Field(max_length=MAX_SKILLS)


class LanguageWrite(BaseModel):
    id: uuid.UUID | None = None
    language: LanguageName = Field(examples=["Inglés"])
    level: LanguageLevel


class LanguageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    language: str
    level: LanguageLevel


class LanguagesUpdate(BaseModel):
    languages: list[LanguageWrite] = Field(max_length=MAX_LANGUAGES)
