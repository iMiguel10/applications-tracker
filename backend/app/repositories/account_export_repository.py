import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_consent import AiConsent
from app.models.ai_proposal import AiProposal
from app.models.ai_provider_key import AiProviderKey
from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.models.document import Document
from app.models.interview import Interview
from app.models.profile import Profile
from app.models.profile_entry import ProfileEntry, ProfileEntryBullet
from app.models.profile_skill import ProfileLanguage, ProfileSkill
from app.models.reminder import Reminder
from app.models.user import User


def _statement(table: str, user_id: uuid.UUID) -> Select[Any]:
    """La consulta de cada tabla exportada, siempre filtrada por la cuenta: las hijas
    sin `user_id` propio, a través de su padre. Ordenadas para que dos exportaciones
    de los mismos datos salgan iguales."""
    match table:
        case "companies":
            return (
                select(Company)
                .where(Company.user_id == user_id)
                .order_by(Company.created_at, Company.id)
            )
        case "applications":
            return (
                select(Application)
                .where(Application.user_id == user_id)
                .order_by(Application.created_at, Application.id)
            )
        case "application_status_changes":
            return (
                select(ApplicationStatusChange)
                .join(Application)
                .where(Application.user_id == user_id)
                .order_by(ApplicationStatusChange.seq)
            )
        case "interviews":
            return (
                select(Interview)
                .join(Application)
                .where(Application.user_id == user_id)
                .order_by(Interview.scheduled_at, Interview.id)
            )
        case "reminders":
            return (
                select(Reminder)
                .where(Reminder.user_id == user_id)
                .order_by(Reminder.created_at, Reminder.id)
            )
        case "documents":
            return (
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.created_at, Document.id)
            )
        case "profiles":
            return select(Profile).where(Profile.user_id == user_id)
        case "profile_entries":
            return (
                select(ProfileEntry)
                .join(Profile)
                .where(Profile.user_id == user_id)
                .order_by(ProfileEntry.kind, ProfileEntry.position)
            )
        case "profile_entry_bullets":
            return (
                select(ProfileEntryBullet)
                .join(ProfileEntry)
                .join(Profile)
                .where(Profile.user_id == user_id)
                .order_by(ProfileEntryBullet.entry_id, ProfileEntryBullet.position)
            )
        case "profile_skills":
            return (
                select(ProfileSkill)
                .join(Profile)
                .where(Profile.user_id == user_id)
                .order_by(ProfileSkill.position)
            )
        case "profile_languages":
            return (
                select(ProfileLanguage)
                .join(Profile)
                .where(Profile.user_id == user_id)
                .order_by(ProfileLanguage.position)
            )
        case "ai_proposals":
            return (
                select(AiProposal)
                .where(AiProposal.user_id == user_id)
                .order_by(AiProposal.created_at, AiProposal.id)
            )
        case "ai_consents":
            return (
                select(AiConsent)
                .where(AiConsent.user_id == user_id)
                .order_by(AiConsent.granted_at, AiConsent.id)
            )
        case "ai_provider_keys":
            return (
                select(AiProviderKey)
                .where(AiProviderKey.user_id == user_id)
                .order_by(AiProviderKey.created_at, AiProviderKey.id)
            )
    raise ValueError(f"Tabla sin consulta de exportación: {table}")


class AccountExportRepository:
    """Lecturas de la exportación completa de una cuenta (issue #4): todas las filas
    de cada tabla que pertenecen a un usuario. Solo lee."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def rows(self, table: str, user_id: uuid.UUID) -> Sequence[Any]:
        result = await self.session.scalars(_statement(table, user_id))
        return result.all()
