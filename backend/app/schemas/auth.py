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


class UnauthorizedError(BaseModel):
    """Respuesta 401 de SuperTokens: no hay sesión, o el token ha caducado o es inválido."""

    message: Literal["unauthorised"]
