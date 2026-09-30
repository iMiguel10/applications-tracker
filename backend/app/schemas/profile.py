from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
)

from app.domain.profile import (
    CONTACT_EMAIL_MAX_LENGTH,
    LINK_LABEL_MAX_LENGTH,
    LINK_URL_MAX_LENGTH,
    MAX_LINKS,
    PHONE_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
    is_safe_link,
)
from app.schemas.common import OptionalShortText, empty_to_none


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
