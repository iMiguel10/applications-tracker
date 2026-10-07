import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ai import AiProvider
from app.models.ai_consent import AiConsent


class AiConsentRepository:
    """Acceso a `ai_consents`. Todo método recibe `user_id` y filtra por él
    (invariante 1). Nunca hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID, provider: AiProvider) -> AiConsent | None:
        return await self.session.scalar(
            select(AiConsent).where(
                AiConsent.user_id == user_id, AiConsent.provider == provider.value
            )
        )

    async def list(self, user_id: uuid.UUID) -> Sequence[AiConsent]:
        result = await self.session.scalars(
            select(AiConsent)
            .where(AiConsent.user_id == user_id)
            .order_by(AiConsent.provider)
        )
        return result.all()

    async def grant(
        self,
        user_id: uuid.UUID,
        provider: AiProvider,
        text_version: int,
        now: datetime,
    ) -> None:
        """Da (o renueva) el consentimiento con la versión actual del texto. Con
        `ON CONFLICT`: dos peticiones a la vez no chocan con la clave única."""
        values = {"text_version": text_version, "granted_at": now, "revoked_at": None}
        await self.session.execute(
            insert(AiConsent)
            .values(user_id=user_id, provider=provider.value, **values)
            .on_conflict_do_update(
                index_elements=[AiConsent.user_id, AiConsent.provider], set_=values
            )
        )

    async def revoke(
        self, user_id: uuid.UUID, provider: AiProvider, now: datetime
    ) -> None:
        await self.session.execute(
            update(AiConsent)
            .where(
                AiConsent.user_id == user_id,
                AiConsent.provider == provider.value,
                AiConsent.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
