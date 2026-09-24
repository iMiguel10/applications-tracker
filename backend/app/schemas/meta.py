from pydantic import BaseModel, Field


class MetaRead(BaseModel):
    email_enabled: bool = Field(
        description="`true` si esta instalación tiene un servidor de correo "
        "configurado. Sin él no se envían emails: la recuperación de contraseña y "
        "la verificación de email no están disponibles.",
        examples=[True],
    )
