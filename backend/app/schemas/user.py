import uuid
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)

from app.domain.legal import LEGAL_VERSION_MAX_LENGTH
from app.domain.notifications import (
    MAX_INTERVIEW_NOTICE_HOURS,
    MAX_REMINDER_NOTICE_HOURS,
    MIN_INTERVIEW_NOTICE_HOURS,
    MIN_REMINDER_NOTICE_HOURS,
)
from app.domain.user import (
    MAX_STALE_AFTER_DAYS,
    MAX_TIMEZONE_LENGTH,
    MIN_STALE_AFTER_DAYS,
    Language,
    is_valid_timezone,
)


class CurrentUser(BaseModel):
    """Usuario de la petición en curso, entregado por get_current_user."""

    id: uuid.UUID
    supertokens_user_id: str


def _no_default_in_schema(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


# Las dos contraseñas son SecretStr, sin restricciones y con un valor por defecto
# vacío, a propósito: Pydantic pone en cualquier error de validación la entrada
# original, en claro, y si falta un campo, el cuerpo entero, así que el 422
# devolvería la contraseña. El schema no falla por ellas, y el service rechaza lo
# que no vale: una actual vacía es una actual incorrecta, y una nueva vacía o
# demasiado larga no cumple la política. En el contrato siguen siendo obligatorias.
class PasswordChange(BaseModel):
    """Cambiar la contraseña con la actual. Las dos son obligatorias."""

    model_config = ConfigDict(
        json_schema_extra={"required": ["current_password", "new_password"]}
    )

    current_password: SecretStr = Field(
        default=SecretStr(""),
        description="La contraseña actual.",
        json_schema_extra=_no_default_in_schema,
    )
    new_password: SecretStr = Field(
        default=SecretStr(""),
        description="La contraseña nueva. Debe cumplir la política de contraseñas "
        "(entre 8 y 100 caracteres, con letras y números); si no, 422 "
        "`password_policy`.",
        json_schema_extra=_no_default_in_schema,
    )


class MeRead(BaseModel):
    id: uuid.UUID = Field(description="Identificador del usuario en esta API.")
    email: str | None = Field(
        description="Email de la cuenta, leído de SuperTokens en cada petición.",
        examples=["ana@example.com"],
    )
    legal_accepted_version: str | None = Field(
        default=None,
        description="Versión de los términos y la política de privacidad que "
        "aceptó la cuenta (`null`: ninguna). Si la instalación los tiene "
        "(`legal.configured` en `GET /meta`) y no coincide con `legal.version`, "
        "debe aceptar la vigente con `POST /me/legal-acceptance`.",
        examples=["2026-10-20"],
    )


class LegalAcceptance(BaseModel):
    version: str = Field(
        max_length=LEGAL_VERSION_MAX_LENGTH,
        description="La versión que se acepta: la de `legal.version` en `GET /meta`.",
        examples=["2026-10-20"],
    )


StaleAfterDays = Annotated[int, Field(ge=MIN_STALE_AFTER_DAYS, le=MAX_STALE_AFTER_DAYS)]
InterviewNoticeHours = Annotated[
    int, Field(ge=MIN_INTERVIEW_NOTICE_HOURS, le=MAX_INTERVIEW_NOTICE_HOURS)
]
ReminderNoticeHours = Annotated[
    int, Field(ge=MIN_REMINDER_NOTICE_HOURS, le=MAX_REMINDER_NOTICE_HOURS)
]


def _known_timezone(value: str) -> str:
    if not is_valid_timezone(value):
        raise ValueError("Unknown time zone: use an IANA name such as Europe/Madrid")
    return value


Timezone = Annotated[
    str,
    Field(max_length=MAX_TIMEZONE_LENGTH, examples=["Europe/Madrid"]),
    AfterValidator(_known_timezone),
]


class PreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language | None = Field(
        description="`null`: sigue el idioma del navegador."
    )
    stale_after_days: StaleAfterDays = Field(
        description="RF-64: días sin actividad para avisar en el dashboard."
    )
    timezone: str | None = Field(
        description="RF-07: zona horaria IANA (`Europe/Madrid`). `null` hasta que "
        "el cliente la fija; mientras tanto se usa UTC.",
        examples=["Europe/Madrid"],
    )
    notify_reminder_due: bool = Field(
        description="RF-80: email cuando vence un recordatorio pendiente."
    )
    notify_interview: bool = Field(
        description="RF-81: email antes de cada entrevista programada."
    )
    notify_weekly_digest: bool = Field(
        description="RF-82: resumen semanal, el lunes por la mañana."
    )
    notify_stale: bool = Field(
        description="RF-83: aviso cuando una solicitud se queda sin actividad."
    )
    notify_ai_proposal: bool = Field(
        description="RF-157: email cuando termina una propuesta de IA (CV o carta)."
    )
    reminder_notice_hours: ReminderNoticeHours = Field(
        description="RF-80: horas de antelación del aviso de recordatorio; 0 avisa "
        "al vencer."
    )
    interview_notice_hours: InterviewNoticeHours = Field(
        description="RF-81: horas de antelación del aviso de entrevista."
    )


# Campos en los que `null` no significa nada: enviarlo explícitamente es un 422,
# no un NULL que la BD rechazaría con un 500.
_NOT_NULLABLE = frozenset(
    {
        "stale_after_days",
        "notify_reminder_due",
        "notify_interview",
        "notify_weekly_digest",
        "notify_stale",
        "notify_ai_proposal",
        "reminder_notice_hours",
        "interview_notice_hours",
    }
)


class PreferencesUpdate(BaseModel):
    """Solo cambia los campos que se envían. `null` solo vale en `language`
    (seguir al navegador) y `timezone`."""

    language: Language | None = None
    stale_after_days: StaleAfterDays | None = None
    timezone: Timezone | None = Field(
        default=None,
        description="Nombre IANA de una zona conocida; otro valor responde 422. "
        "La aplicación web envía la del navegador si la cuenta aún no tiene.",
    )
    notify_reminder_due: bool | None = None
    notify_interview: bool | None = None
    notify_weekly_digest: bool | None = None
    notify_stale: bool | None = None
    notify_ai_proposal: bool | None = None
    reminder_notice_hours: ReminderNoticeHours | None = None
    interview_notice_hours: InterviewNoticeHours | None = None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        nulls = sorted(
            field
            for field in self.model_fields_set & _NOT_NULLABLE
            if getattr(self, field) is None
        )
        if nulls:
            raise ValueError(f"Cannot be null: {', '.join(nulls)}")
        return self
