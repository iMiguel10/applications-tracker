import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException
from app.domain.ai import AI_CONSENT_VERSION, AiProvider
from app.infra.llm import platform_model
from app.models.ai_consent import AiConsent
from app.repositories.ai_consent_repository import AiConsentRepository
from app.schemas.ai import AiConsentRead, AiConsentsRead


def consent_is_current(consent: AiConsent | None) -> bool:
    """Vigente: dado sobre la versión actual del texto y sin retirar (ia.md §8)."""
    return (
        consent is not None
        and consent.revoked_at is None
        and consent.text_version == AI_CONSENT_VERSION
    )


class AiConsentService:
    """Consentimiento por proveedor para enviarle datos del perfil (RF-116,
    RF-154). Se da o se retira por proveedor: el de la plataforma o, con las claves
    propias, el que elija el usuario."""

    def __init__(self, session: AsyncSession, config: Settings = settings) -> None:
        self.session = session
        self.config = config
        self.consents = AiConsentRepository(session)

    def offered_providers(self) -> set[AiProvider]:
        """Los proveedores a los que esta instalación puede enviar datos: el de la
        plataforma y los que tienen modelos para claves propias (0017)."""
        offered = {
            provider for provider in AiProvider if self.config.ai_models(provider)
        }
        platform = platform_model(self.config)
        if platform is not None:
            offered.add(platform.provider)
        return offered

    async def has_consent(self, user_id: uuid.UUID, provider: AiProvider) -> bool:
        return consent_is_current(await self.consents.get(user_id, provider))

    async def overview(self, user_id: uuid.UUID) -> AiConsentsRead:
        platform = platform_model(self.config)
        return AiConsentsRead(
            text_version=AI_CONSENT_VERSION,
            platform_provider=platform.provider if platform else None,
            platform_model=platform.model if platform else None,
            consents=[
                AiConsentRead(
                    provider=AiProvider(consent.provider),
                    granted=consent_is_current(consent),
                    granted_at=consent.granted_at,
                    revoked_at=consent.revoked_at,
                )
                for consent in await self.consents.list(user_id)
            ],
        )

    async def grant(self, user_id: uuid.UUID, provider: AiProvider) -> AiConsentsRead:
        """Da el consentimiento para `provider` con la versión actual del texto.
        Solo a un proveedor que esta instalación ofrece: consentir a uno que no se
        puede usar no tiene sentido y confundiría al volver a habilitarlo."""
        if provider not in self.offered_providers():
            raise AppException(
                "AI provider not offered",
                status_code=422,
                code="ai_provider_not_offered",
            )
        await self.consents.grant(
            user_id, provider, AI_CONSENT_VERSION, datetime.now(UTC)
        )
        await self.session.commit()
        return await self.overview(user_id)

    async def revoke(self, user_id: uuid.UUID, provider: AiProvider) -> None:
        """Retira el consentimiento (RF-116). Las propuestas ya hechas se quedan:
        lo que se envió, enviado está; desde ahora no se envía nada más."""
        await self.consents.revoke(user_id, provider, datetime.now(UTC))
        await self.session.commit()
