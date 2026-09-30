from typing import Literal, Self

from pydantic import Field, model_validator
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

    # Secreto de la instalación para firmar enlaces que funcionan sin sesión (la
    # baja de avisos, RF-85). Obligatorio y largo: quien lo conozca puede darse de
    # baja en nombre de cualquiera. Cambiarlo invalida los enlaces ya enviados.
    app_secret: str = Field(min_length=32)

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

    # Límites por usuario (especificación §10, RF-140). Valores globales de la
    # instalación; una cuenta concreta puede tener otro con
    # scripts/set_user_limit.py (RF-143). Los nombres siguen domain/limits.py.
    limit_applications: int = Field(default=5_000, ge=0)
    limit_companies: int = Field(default=2_000, ge=0)
    limit_reminders: int = Field(default=5_000, ge=0)
    limit_documents: int = Field(default=100, ge=0)
    # En bytes (100 MB). Tope siempre: no admite excepciones "sin límite".
    limit_storage_bytes: int = Field(default=100 * 1024 * 1024, ge=0)
    # Tamaño máximo de un PDF subido (5 MB). No es un límite por cuenta: vale para
    # todas y lo publica GET /meta para que la interfaz avise antes de subir.
    document_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)

    # Rate limiting (RNF-04, límites y abuso §2). Desactivable solo para las
    # pruebas, que si no fallarían de forma intermitente por 429.
    rate_limit_enabled: bool = True
    # IPs o redes (CIDR) de los proxies cuyo X-Forwarded-For se acepta, separadas
    # por comas. Vacío (desarrollo, sin proxy): se usa la IP de la conexión.
    trusted_proxies: str = ""

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
