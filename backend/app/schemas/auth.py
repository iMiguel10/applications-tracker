"""Contrato de las rutas /auth/* de SuperTokens, solo para documentar el OpenAPI.

Esas rutas las sirve el middleware de SuperTokens y no pasan por FastAPI: estos
modelos describen lo que el middleware acepta y devuelve (capturado de respuestas
reales del SDK), no se usan para validar nada.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FormField(BaseModel):
    id: Literal["email", "password"] = Field(description="Nombre del campo.")
    value: str = Field(description="Valor del campo.")


class AuthCredentials(BaseModel):
    """Cuerpo de registro y login: lista de campos en el formato de SuperTokens."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "formFields": [
                        {"id": "email", "value": "ana@example.com"},
                        {"id": "password", "value": "secreto123"},
                    ]
                }
            ]
        }
    )

    formFields: list[FormField] = Field(
        description="Exactamente dos campos: `email` y `password`."
    )


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Id del usuario en SuperTokens.")
    emails: list[str]


class AuthOk(BaseModel):
    status: Literal["OK"]
    user: AuthUser


class AuthWrongCredentials(BaseModel):
    """Email o contraseña incorrectos. No indica cuál de los dos falla."""

    status: Literal["WRONG_CREDENTIALS_ERROR"]


class AuthFieldErrorItem(BaseModel):
    id: Literal["email", "password"]
    error: str = Field(
        description="Mensaje en inglés de SuperTokens. Los clientes deben traducir "
        "por `id`, no por el texto.",
        examples=["This email already exists. Please sign in instead."],
    )


class AuthFieldError(BaseModel):
    """Algún campo no es válido: email con formato incorrecto o ya registrado,
    o contraseña que no cumple la política (mínimo 8 caracteres, con letras y
    números)."""

    status: Literal["FIELD_ERROR"]
    formFields: list[AuthFieldErrorItem]


class AuthStatusOk(BaseModel):
    status: Literal["OK"]


class EmailField(BaseModel):
    id: Literal["email"]
    value: str


class PasswordField(BaseModel):
    id: Literal["password"]
    value: str


class PasswordResetTokenRequest(BaseModel):
    """Cuerpo para pedir el email de recuperación."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"formFields": [{"id": "email", "value": "ana@example.com"}]}]
        }
    )

    formFields: list[EmailField] = Field(description="Un solo campo: `email`.")


class PasswordResetRequest(BaseModel):
    """Cuerpo para guardar la contraseña nueva con el token del enlace."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "method": "token",
                    "token": "<token del enlace>",
                    "formFields": [{"id": "password", "value": "nueva-clave-42"}],
                }
            ]
        }
    )

    method: Literal["token"]
    token: str = Field(
        description="El parámetro `token` del enlace del email. Sirve una sola vez "
        "y caduca a la hora."
    )
    formFields: list[PasswordField] = Field(description="Un solo campo: `password`.")


class AuthResetInvalidToken(BaseModel):
    """El token ya se usó, ha caducado o no existe: hay que pedir otro enlace."""

    status: Literal["RESET_PASSWORD_INVALID_TOKEN_ERROR"]


class UnauthorizedError(BaseModel):
    """Respuesta 401 de SuperTokens: no hay sesión, o el token ha caducado o es inválido."""

    message: Literal["unauthorised"]


class EmailVerifyRequest(BaseModel):
    """Cuerpo para verificar el email con el token del enlace."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"method": "token", "token": "<token del enlace>"}]
        }
    )

    method: Literal["token"]
    token: str = Field(
        description="El parámetro `token` del enlace del email. Caduca en 24 horas."
    )


class EmailVerifyInvalidToken(BaseModel):
    """El token ya se usó, ha caducado o no existe: se puede pedir otro enlace."""

    status: Literal["EMAIL_VERIFICATION_INVALID_TOKEN_ERROR"]


class EmailAlreadyVerified(BaseModel):
    """El email ya está verificado: no se envía nada."""

    status: Literal["EMAIL_ALREADY_VERIFIED_ERROR"]


class EmailVerifiedStatus(BaseModel):
    status: Literal["OK"]
    isVerified: bool = Field(
        description="Si el email de la sesión está verificado, según el core. "
        "Consultarlo también actualiza ese dato dentro del access token."
    )
