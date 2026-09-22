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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


settings = Settings()
