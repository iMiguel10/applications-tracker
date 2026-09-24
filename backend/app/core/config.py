from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str
    database_url: str

    cors_origins: str = ""

    # SuperTokens. Sin valores por defecto: si falta alguno, la API no arranca
    # (mejor que descubrirlo en el primer login).
    api_domain: str
    website_domain: str
    supertokens_connection_uri: str
    supertokens_api_key: str

    # Cola de trabajos (SAQ sobre Valkey, A18). Obligatoria: sin cola, las
    # operaciones lentas no tienen dónde ejecutarse (RNF-12).
    valkey_url: str

    # Raíz del almacén de ficheros (A21): el volumen files_data, compartido por
    # api y worker. Obligatoria.
    files_root: str

    # Correo (RNF-34). Opcional a propósito: sin SMTP_HOST la aplicación arranca
    # igual y lo que depende del email aparece como no disponible. El servidor lo
    # configura quien despliega; la aplicación no depende de ningún proveedor.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_security: Literal["none", "starttls", "tls"] = "starttls"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_timeout_seconds: float = 30
    email_from: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _email_from_required_with_smtp(self) -> Self:
        # Un SMTP configurado a medias fallaría en el primer envío, horas después
        # de arrancar. Mejor no arrancar.
        if self.smtp_host and not self.email_from:
            raise ValueError("EMAIL_FROM es obligatorio si se configura SMTP_HOST")
        return self

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host)

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


settings = Settings()
