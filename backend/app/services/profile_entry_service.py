import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, LimitReachedError, NotFoundError
from app.domain.profile import MAX_ENTRIES
from app.models.profile_entry import ProfileEntry, ProfileEntryBullet
from app.repositories.profile_entry_repository import ProfileEntryRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import (
    BulletWrite,
    EntryCreate,
    EntryFields,
    EntryOrder,
    EntryUpdate,
)

# Campos de la entrada que se copian tal cual del schema.
_ENTRY_FIELDS = (
    "title",
    "organization",
    "location",
    "start_date",
    "end_date",
    "is_current",
    "description",
)


class ProfileEntryService:
    """Experiencia, formación, proyectos y certificaciones del perfil (RF-101,
    RF-102). Dueño de la transacción: es quien hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = ProfileRepository(session)
        self.entries = ProfileEntryRepository(session)

    async def list(self, user_id: uuid.UUID) -> Sequence[ProfileEntry]:
        return await self.entries.list(user_id)

    async def create(self, user_id: uuid.UUID, data: EntryCreate) -> ProfileEntry:
        profile = await self.profiles.get_or_create(user_id)
        # Tope de la sección con el perfil bloqueado: dos altas a la vez no se
        # pasan juntas (como las cuotas con coste, A30).
        await self.profiles.lock(profile.id)
        used = await self.entries.count(user_id, data.kind)
        limit = MAX_ENTRIES[data.kind]
        if used >= limit:
            raise LimitReachedError("profile_section_full", limit=limit, used=used)

        entry = ProfileEntry(
            profile_id=profile.id,
            kind=data.kind.value,
            position=await self.entries.next_position(user_id, data.kind),
            bullets=[],
        )
        self._apply(entry, data)
        await self.entries.add(entry)
        await self.session.commit()
        return await self._reload(user_id, entry.id)

    async def update(
        self, user_id: uuid.UUID, entry_id: uuid.UUID, data: EntryUpdate
    ) -> ProfileEntry:
        entry = await self._get(user_id, entry_id)
        self._apply(entry, data)
        await self.entries.save(entry)
        await self.session.commit()
        return await self._reload(user_id, entry_id)

    async def delete(self, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
        entry = await self._get(user_id, entry_id)
        await self.entries.delete(entry)
        await self.session.commit()

    async def reorder(
        self, user_id: uuid.UUID, order: EntryOrder
    ) -> Sequence[ProfileEntry]:
        """El orden nuevo de una sección. Debe traer exactamente sus ids: uno de
        más (de otra sección o de otro usuario), uno de menos o uno repetido es un
        422, no un orden a medias."""
        existing = await self.entries.ids(user_id, order.kind)
        if (
            len(order.entry_ids) != len(set(order.entry_ids))
            or set(order.entry_ids) != existing
        ):
            raise AppException(
                "The order must list every entry of the section exactly once",
                status_code=422,
                code="entry_order_mismatch",
            )
        await self.entries.set_positions(user_id, order.entry_ids)
        await self.session.commit()
        return await self.entries.list(user_id)

    async def _get(self, user_id: uuid.UUID, entry_id: uuid.UUID) -> ProfileEntry:
        entry = await self.entries.get(user_id, entry_id)
        if entry is None:
            raise NotFoundError("Profile entry")
        return entry

    async def _reload(self, user_id: uuid.UUID, entry_id: uuid.UUID) -> ProfileEntry:
        # Tras el commit los atributos caducan: se relee con sus logros.
        self.session.expire_all()
        return await self._get(user_id, entry_id)

    def _apply(self, entry: ProfileEntry, data: EntryFields) -> None:
        for field in _ENTRY_FIELDS:
            setattr(entry, field, getattr(data, field))
        entry.bullets = _merge_bullets(entry.bullets, data.bullets)


def _merge_bullets(
    current: Sequence[ProfileEntryBullet], wanted: Sequence[BulletWrite]
) -> list[ProfileEntryBullet]:
    """Los logros en el orden pedido. Uno con `id` es el existente con ese id: se
    edita en su sitio y conserva su identidad (F15 los referencia por id). Uno sin
    `id` es nuevo. Los que no vienen se borran (`delete-orphan`)."""
    by_id = {bullet.id: bullet for bullet in current}
    merged: list[ProfileEntryBullet] = []
    for position, item in enumerate(wanted):
        if item.id is None:
            merged.append(ProfileEntryBullet(text=item.text, position=position))
            continue
        bullet = by_id.pop(item.id, None)
        if bullet is None:
            # Un id de otra entrada (o inventado): no se "roba" ni se crea con él.
            raise AppException(
                "Bullet does not belong to this entry",
                status_code=422,
                code="bullet_not_in_entry",
            )
        bullet.text = item.text
        bullet.position = position
        merged.append(bullet)
    return merged
