from typing import Literal, Self

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.ai import AiProvider
from app.infra.crypto import parse_master_keys


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
    # Usos gratuitos de IA por cuenta y tarea, con la plataforma (0017). Sin renovar.
    limit_ai_cv_proposals: int = Field(default=1, ge=0)
    limit_ai_cover_letter_proposals: int = Field(default=1, ge=0)

    # Rate limiting (RNF-04, límites y abuso §2). Desactivable solo para las
    # pruebas, que si no fallarían de forma intermitente por 429.
    rate_limit_enabled: bool = True
    # IPs o redes (CIDR) de los proxies cuyo X-Forwarded-For se acepta, separadas
    # por comas. Vacío (desarrollo, sin proxy): se usa la IP de la conexión.
    trusted_proxies: str = ""

    # IA (F15, decisión 0017). La plataforma: proveedor, modelo y clave con los que
    # se sirven los usos gratuitos. Sin proveedor, la instalación no tiene uso
    # gratuito y la IA solo funciona con claves propias.
    ai_platform_provider: AiProvider | None = None
    ai_platform_model: str | None = None
    ai_platform_api_key: str | None = None
    # Precio por millón de tokens del modelo de la plataforma, en dólares. Solo
    # estima el coste de cada propuesta (cost_micros): no hay tope de gasto (0017).
    ai_platform_input_usd_per_mtok: float = Field(default=0, ge=0)
    ai_platform_output_usd_per_mtok: float = Field(default=0, ge=0)
    # Modelos que un usuario puede elegir con su clave propia, separados por comas;
    # el primero es el de por defecto. Un proveedor con la lista vacía no se ofrece.
    ai_anthropic_models: str = ""
    ai_openai_models: str = ""
    ai_groq_models: str = ""
    # Dirección de un Ollama propio (p. ej. http://ollama:11434), para usarlo como IA
    # de la plataforma. La fija quien despliega; nunca un usuario.
    ai_ollama_base_url: str | None = None
    # Claves maestras (Fernet) con que se cifran las claves de API de los usuarios,
    # separadas por comas: se cifra con la primera y se descifra con cualquiera
    # (rotación, ia.md §7). Sin ellas no se ofrecen claves propias.
    ai_keys_encryption_keys: str = ""
    # Una propuesta tarda segundos; un modelo que razona, algo más. Sin tope, un
    # proveedor colgado retendría al worker indefinidamente.
    ai_request_timeout_seconds: float = Field(default=120, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @field_validator(
        "ai_platform_provider",
        "ai_platform_model",
        "ai_platform_api_key",
        "ai_ollama_base_url",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        # AI_PLATFORM_PROVIDER= en el .env es "sin plataforma", no un proveedor
        # llamado "" (que el enumerado rechazaría al arrancar).
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _platform_complete(self) -> Self:
        # Una plataforma configurada a medias fallaría en el primer uso gratuito,
        # dentro del worker. Mejor no arrancar.
        provider = self.ai_platform_provider
        if provider is None:
            return self
        if provider == AiProvider.OLLAMA:
            # Sin clave, pero con su dirección.
            if not (self.ai_platform_model and self.ai_ollama_base_url):
                raise ValueError(
                    "AI_PLATFORM_MODEL y AI_OLLAMA_BASE_URL son obligatorias "
                    "con AI_PLATFORM_PROVIDER=ollama"
                )
        elif not (self.ai_platform_model and self.ai_platform_api_key):
            raise ValueError(
                "AI_PLATFORM_MODEL y AI_PLATFORM_API_KEY son obligatorias "
                "si se configura AI_PLATFORM_PROVIDER"
            )
        return self

    @model_validator(mode="after")
    def _encryption_keys_valid(self) -> Self:
        # Una clave maestra mal copiada fallaría al guardar la primera clave de un
        # usuario. Mejor no arrancar.
        for key in parse_master_keys(self.ai_keys_encryption_keys):
            try:
                Fernet(key.encode())
            except ValueError:
                raise ValueError(
                    "AI_KEYS_ENCRYPTION_KEYS: cada clave debe ser una clave Fernet "
                    "(genera una con python -m app.scripts.rotate_ai_keys --new-key)"
                ) from None
        return self

    @property
    def ai_own_keys_enabled(self) -> bool:
        """Si los usuarios pueden guardar su clave: hacen falta claves maestras."""
        return bool(parse_master_keys(self.ai_keys_encryption_keys))

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

    def ai_models(self, provider: AiProvider) -> list[str]:
        """Modelos que un usuario puede elegir con su clave de `provider`, en orden
        (el primero es el de por defecto). Vacía: el proveedor no se ofrece."""
        raw = {
            AiProvider.ANTHROPIC: self.ai_anthropic_models,
            AiProvider.OPENAI: self.ai_openai_models,
            AiProvider.GROQ: self.ai_groq_models,
        }.get(provider, "")
        models: list[str] = []
        for model in (item.strip() for item in raw.split(",")):
            if model and model not in models:
                models.append(model)
        return models

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


settings = Settings()
