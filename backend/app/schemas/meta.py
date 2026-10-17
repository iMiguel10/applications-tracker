from pydantic import BaseModel, Field


class MetaRead(BaseModel):
    email_enabled: bool = Field(
        description="`true` si esta instalación tiene un servidor de correo "
        "configurado. Sin él no se envían emails: la recuperación de contraseña y "
        "la verificación de email no están disponibles.",
        examples=[True],
    )
    signup_enabled: bool = Field(
        description="`false` si el registro está cerrado: `POST /auth/signup` "
        "responde `GENERAL_ERROR` con el mensaje `signup_disabled` y las cuentas "
        "las crea quien administra la instalación.",
        examples=[True],
    )
    max_document_bytes: int = Field(
        description="Tamaño máximo en bytes de un PDF subido a la biblioteca. Un "
        "cliente puede avisar antes de subir uno más grande, que la API rechaza con "
        "413 `file_too_large`.",
        examples=[5242880],
    )
