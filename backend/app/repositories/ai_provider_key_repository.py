import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ai import AiProvider
from app.models.ai_provider_key import AiProviderKey


class AiProviderKeyRepository:
    """Acceso a `ai_provider_keys`. Todo método sobre las claves de un usuario
    recibe `user_id` y filtra por él (invariante 1); solo la rotación de la clave
    maestra, un script de mantenimiento, las recorre todas. Nunca hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, user_id: uuid.UUID, provider: AiProvider
    ) -> AiProviderKey | None:
        return await self.session.scalar(
            select(AiProviderKey).where(
                AiProviderKey.user_id == user_id,
                AiProviderKey.provider == provider.value,
            )
        )

    async def list(self, user_id: uuid.UUID) -> Sequence[AiProviderKey]:
        result = await self.session.scalars(
            select(AiProviderKey)
            .where(AiProviderKey.user_id == user_id)
            .order_by(AiProviderKey.provider)
        )
        return result.all()

    async def save(
        self,
        user_id: uuid.UUID,
        provider: AiProvider,
        *,
        model: str,
        ciphertext: bytes,
        last4: str,
        validated_at: datetime,
    ) -> None:
        """Guarda la clave de ese proveedor, o sustituye la que hubiera. Con
        `ON CONFLICT`: dos guardados a la vez no chocan con la clave única."""
        values = {
            "model": model,
            "ciphertext": ciphertext,
            "last4": last4,
            "validated_at": validated_at,
        }
        await self.session.execute(
            insert(AiProviderKey)
            .values(user_id=user_id, provider=provider.value, **values)
            .on_conflict_do_update(
                index_elements=[AiProviderKey.user_id, AiProviderKey.provider],
                set_=values,
            )
        )

    async def set_model(
        self, user_id: uuid.UUID, provider: AiProvider, model: str
    ) -> None:
        await self.session.execute(
            update(AiProviderKey)
            .where(
                AiProviderKey.user_id == user_id,
                AiProviderKey.provider == provider.value,
            )
            .values(model=model)
        )

    async def delete(self, user_id: uuid.UUID, provider: AiProvider) -> bool:
        result = await self.session.execute(
            delete(AiProviderKey)
            .where(
                AiProviderKey.user_id == user_id,
                AiProviderKey.provider == provider.value,
            )
            .returning(AiProviderKey.id)
        )
        return result.first() is not None

    async def all_for_rotation(
        self, limit: int, after: uuid.UUID | None = None
    ) -> Sequence[AiProviderKey]:
        """Una página de todas las claves, por id, bloqueadas hasta el commit: solo
        para volver a cifrarlas con la clave maestra nueva (rotación, ia.md §7)."""
        query = select(AiProviderKey).order_by(AiProviderKey.id).limit(limit)
        if after is not None:
            query = query.where(AiProviderKey.id > after)
        result = await self.session.scalars(query.with_for_update())
        return result.all()
