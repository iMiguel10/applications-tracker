from pydantic import BaseModel, Field

from app.domain.ai import AiProvider


class LegalRead(BaseModel):
    """Lo que necesitan las páginas legales de la instalación (issue #3): quién es
    el responsable de los datos y lo que la instalación tiene activo."""

    configured: bool = Field(
        description="`false` si quien despliega no ha puesto su nombre y contacto: "
        "la instalación se trata como de uso personal, sin enlaces a las páginas "
        "legales ni aceptación.",
        examples=[True],
    )
    version: str = Field(
        description="Versión vigente de los términos y la política de privacidad. "
        "Una cuenta que aceptó otra (`legal_accepted_version` en `GET /me`) debe "
        "aceptar esta.",
        examples=["2026-10-20"],
    )
    operator_name: str | None = Field(
        description="Responsable del tratamiento: persona o entidad.",
        examples=["Ana García"],
    )
    contact_email: str | None = Field(
        description="Contacto para dudas y para ejercer los derechos.",
        examples=["privacidad@example.com"],
    )
    address: str | None = Field(
        description="Dirección postal, si quien despliega la publica.",
        examples=["Calle Mayor 1, 28001 Madrid"],
    )
    tax_id: str | None = Field(
        description="Identificación fiscal (NIF), si quien despliega la publica.",
        examples=["12345678Z"],
    )
    supervisory_authority: str | None = Field(
        description="Autoridad de control ante la que reclamar. `null`: la "
        "española (AEPD).",
        examples=[None],
    )
    ai_platform_provider: AiProvider | None = Field(
        description="Proveedor de la IA de la plataforma, si hay. Con Anthropic, "
        "OpenAI o Groq los datos salen a EE. UU.; con Ollama, a un servidor que "
        "elige quien despliega.",
        examples=["groq"],
    )
    ai_own_key_providers: list[AiProvider] = Field(
        description="Proveedores con los que cada persona puede usar su propia "
        "clave de IA.",
        examples=[["anthropic", "openai"]],
    )
    backup_retention_days: int = Field(
        description="Días, como mucho, que un dato borrado sigue en las copias de "
        "seguridad.",
        examples=[35],
    )


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
    legal: LegalRead = Field(
        description="Datos de las páginas legales (aviso legal, privacidad, "
        "términos y cookies)."
    )
