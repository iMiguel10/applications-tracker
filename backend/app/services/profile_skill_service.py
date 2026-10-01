import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.domain.profile import name_key
from app.models.profile import Profile
from app.models.profile_skill import ProfileLanguage, ProfileSkill
from app.repositories.profile_repository import ProfileRepository
from app.repositories.profile_skill_repository import ProfileSkillRepository
from app.schemas.profile import LanguagesUpdate, LanguageWrite, SkillsUpdate, SkillWrite


class _Item(Protocol):
    id: uuid.UUID | None


class _Row(Protocol):
    id: uuid.UUID


class ProfileSkillService:
    """Habilidades e idiomas del perfil (RF-102). Cada lista se guarda entera, pero
    cada elemento con `id` conserva su identidad: F15 referencia las habilidades
    por id. Dueño de la transacción: es quien hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = ProfileRepository(session)
        self.items = ProfileSkillRepository(session)

    async def skills(self, user_id: uuid.UUID) -> Sequence[ProfileSkill]:
        return await self.items.skills(user_id)

    async def languages(self, user_id: uuid.UUID) -> Sequence[ProfileLanguage]:
        return await self.items.languages(user_id)

    async def replace_skills(
        self, user_id: uuid.UUID, data: SkillsUpdate
    ) -> Sequence[ProfileSkill]:
        _reject_duplicates([item.name for item in data.skills], "duplicate_skill")
        profile = await self._locked_profile(user_id)

        def assign(row: ProfileSkill, item: SkillWrite, position: int) -> None:
            row.name = item.name
            row.category = item.category
            row.level = item.level.value if item.level else None
            row.position = position

        async with self._duplicates_as_422("duplicate_skill"):
            await self._replace(
                current=await self.items.skills(user_id),
                wanted=data.skills,
                name_attr="name",
                wanted_name=lambda item: item.name,
                assign=assign,
                create=lambda: ProfileSkill(profile_id=profile.id),
                foreign_code="skill_not_in_profile",
            )
            await self.session.commit()
        return await self.items.skills(user_id)

    async def replace_languages(
        self, user_id: uuid.UUID, data: LanguagesUpdate
    ) -> Sequence[ProfileLanguage]:
        _reject_duplicates(
            [item.language for item in data.languages], "duplicate_language"
        )
        profile = await self._locked_profile(user_id)

        def assign(row: ProfileLanguage, item: LanguageWrite, position: int) -> None:
            row.language = item.language
            row.level = item.level.value
            row.position = position

        async with self._duplicates_as_422("duplicate_language"):
            await self._replace(
                current=await self.items.languages(user_id),
                wanted=data.languages,
                name_attr="language",
                wanted_name=lambda item: item.language,
                assign=assign,
                create=lambda: ProfileLanguage(profile_id=profile.id),
                foreign_code="language_not_in_profile",
            )
            await self.session.commit()
        return await self.items.languages(user_id)

    async def _locked_profile(self, user_id: uuid.UUID) -> Profile:
        # Con el perfil bloqueado, dos guardados de la misma lista se ponen en fila
        # en vez de mezclarse.
        profile = await self.profiles.get_or_create(user_id)
        await self.profiles.lock(profile.id)
        return profile

    async def _replace[R: _Row, W: _Item](
        self,
        *,
        current: Sequence[R],
        wanted: Sequence[W],
        name_attr: str,
        wanted_name: Callable[[W], str],
        assign: Callable[[R, W, int], None],
        create: Callable[[], R],
        foreign_code: str,
    ) -> None:
        """Deja la lista como `wanted`, en su orden.

        El índice único `lower(nombre)` se comprueba fila a fila, así que el orden
        de las escrituras importa: primero se borra lo que ya no viene (así
        "react" puede sustituir a un "React" quitado), y los renombrados pasan
        antes por un nombre provisional (así dos filas pueden intercambiarse el
        nombre)."""
        by_id = {row.id: row for row in current}
        kept: list[tuple[R, W, int]] = []
        for position, item in enumerate(wanted):
            if item.id is None:
                continue
            row = by_id.pop(item.id, None)
            if row is None:
                # De otro perfil, inventado o repetido: no se "roba" ni se crea.
                raise AppException(
                    "Item does not belong to this profile",
                    status_code=422,
                    code=foreign_code,
                )
            kept.append((row, item, position))

        for row in by_id.values():
            await self.items.delete(row)
        await self.items.flush()

        renamed = [
            row for row, item, _ in kept if getattr(row, name_attr) != wanted_name(item)
        ]
        for row in renamed:
            setattr(row, name_attr, f"~{row.id}")
        if renamed:
            await self.items.flush()

        for row, item, position in kept:
            assign(row, item, position)
        for position, item in enumerate(wanted):
            if item.id is None:
                row = create()
                assign(row, item, position)
                self.items.add(row)
        await self.items.flush()

    @asynccontextmanager
    async def _duplicates_as_422(self, duplicate_code: str) -> AsyncIterator[None]:
        """La comprobación previa usa `str.lower` y el índice, el `lower()` de
        Postgres, que no coinciden en todo (`'İOS'.lower()` en Python no es
        `'ios'`; en Postgres, sí). El índice puede saltar en cualquier `flush` de
        `_replace`, no solo en el commit: se cubren los dos."""
        try:
            yield
        except IntegrityError as error:
            await self.session.rollback()
            raise _duplicate(duplicate_code) from error


def _reject_duplicates(names: Sequence[str], code: str) -> None:
    keys = [name_key(name) for name in names]
    if len(keys) != len(set(keys)):
        raise _duplicate(code)


def _duplicate(code: str) -> AppException:
    return AppException("Repeated name", status_code=422, code=code)
