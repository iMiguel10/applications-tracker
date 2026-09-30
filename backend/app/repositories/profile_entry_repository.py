import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.profile import EntryKind
from app.models.profile import Profile
from app.models.profile_entry import ProfileEntry


class ProfileEntryRepository:
    """Acceso a `profile_entries` y sus logros. Es una tabla hija (vía `profile_id`):
    se filtra haciendo join con `profiles` para exigir también `user_id`
    (invariante 1).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _owned(self, user_id: uuid.UUID) -> Select[tuple[ProfileEntry]]:
        return (
            select(ProfileEntry)
            .join(Profile, Profile.id == ProfileEntry.profile_id)
            .where(Profile.user_id == user_id)
        )

    async def list(self, user_id: uuid.UUID) -> Sequence[ProfileEntry]:
        """Todas las entradas del usuario con sus logros, por sección y posición."""
        result = await self.session.scalars(
            self._owned(user_id)
            .options(selectinload(ProfileEntry.bullets))
            .order_by(ProfileEntry.kind, ProfileEntry.position, ProfileEntry.id)
        )
        return result.all()

    async def get(self, user_id: uuid.UUID, entry_id: uuid.UUID) -> ProfileEntry | None:
        return await self.session.scalar(
            self._owned(user_id)
            .where(ProfileEntry.id == entry_id)
            .options(selectinload(ProfileEntry.bullets))
        )

    async def count(self, user_id: uuid.UUID, kind: EntryKind) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(ProfileEntry)
            .join(Profile, Profile.id == ProfileEntry.profile_id)
            .where(Profile.user_id == user_id, ProfileEntry.kind == kind)
        )
        return total or 0

    async def next_position(self, user_id: uuid.UUID, kind: EntryKind) -> int:
        """La posición del final de la sección: una entrada nueva va al final."""
        last = await self.session.scalar(
            select(func.max(ProfileEntry.position))
            .join(Profile, Profile.id == ProfileEntry.profile_id)
            .where(Profile.user_id == user_id, ProfileEntry.kind == kind)
        )
        return 0 if last is None else last + 1

    async def ids(self, user_id: uuid.UUID, kind: EntryKind) -> set[uuid.UUID]:
        result = await self.session.scalars(
            select(ProfileEntry.id)
            .join(Profile, Profile.id == ProfileEntry.profile_id)
            .where(Profile.user_id == user_id, ProfileEntry.kind == kind)
        )
        return set(result.all())

    async def set_positions(
        self, user_id: uuid.UUID, ordered_ids: Sequence[uuid.UUID]
    ) -> None:
        """Reescribe las posiciones en el orden dado. El service ya ha comprobado
        que los ids son exactamente los de una sección del usuario; el filtro por
        `user_id` se repite igualmente (invariante 1)."""
        owned = select(Profile.id).where(Profile.user_id == user_id)
        for position, entry_id in enumerate(ordered_ids):
            await self.session.execute(
                update(ProfileEntry)
                .where(
                    ProfileEntry.id == entry_id,
                    ProfileEntry.profile_id.in_(owned),
                )
                .values(position=position)
            )

    async def add(self, entry: ProfileEntry) -> ProfileEntry:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def save(self, entry: ProfileEntry) -> ProfileEntry:
        await self.session.flush()
        return entry

    async def delete(self, entry: ProfileEntry) -> None:
        await self.session.delete(entry)
        await self.session.flush()
