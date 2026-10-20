"""`AccountExportService` (issue #4): todos los datos de la cuenta, nada de otra
cuenta, ningún secreto, y el `.zip` con sus PDF."""

import io
import json
import uuid
import zipfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.account_export import EXPORTED_TABLES, FORMAT_VERSION, table_file
from app.infra.storage import LocalFileStorage
from app.models.ai_consent import AiConsent
from app.models.ai_provider_key import AiProviderKey
from app.models.application_status_change import ApplicationStatusChange
from app.models.notification_delivery import NotificationDelivery
from app.models.profile_skill import ProfileLanguage, ProfileSkill
from app.repositories.identity_repository import IdentityRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.user import CurrentUser
from app.services.account_export_service import AccountExportService
from tests.factories import (
    make_ai_proposal,
    make_application,
    make_document,
    make_interview,
    make_profile_entry,
    make_reminder,
)

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
CIPHERTEXT = b"texto-cifrado-de-la-clave-77"
LAST4 = "Zq9X"


class FakeIdentities(IdentityRepository):
    def __init__(self, emails: dict[str, str]) -> None:
        self.emails = emails

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return self.emails.get(supertokens_user_id)


async def _fill(session: AsyncSession, user: CurrentUser) -> dict[str, set[str]]:
    """Una fila (al menos) en cada tabla exportada; devuelve sus ids por fichero."""
    application = await make_application(session, user.id, notes="Mis notas")
    interview = await make_interview(session, application)
    reminder = await make_reminder(session, user.id, application_id=application.id)
    ready = await make_document(session, user.id, name="CV Ana.pdf")
    pending = await make_document(
        session,
        user.id,
        origin="generated",
        status="pending",
        storage_key=None,
        size_bytes=None,
        sha256=None,
        template="classic",
        language="es",
        content={"profile": {"full_name": "Ana"}},
    )
    entry = await make_profile_entry(session, user.id, bullets=["Logro uno"])
    profile = await ProfileRepository(session).get_or_create(user.id)
    skill = ProfileSkill(profile_id=profile.id, name="Python", position=0)
    language = ProfileLanguage(
        profile_id=profile.id, language="Inglés", level="c1", position=0
    )
    proposal = await make_ai_proposal(session, application)
    consent = AiConsent(
        user_id=user.id, provider="groq", text_version=1, granted_at=NOW
    )
    key = AiProviderKey(
        user_id=user.id,
        provider="openai",
        model="gpt-5.5",
        ciphertext=CIPHERTEXT,
        last4=LAST4,
        validated_at=NOW,
    )
    delivery = NotificationDelivery(
        user_id=user.id,
        kind="weekly_digest",
        dedupe_key="2026-W43",
        status="sent",
        claimed_at=NOW,
    )
    session.add_all([skill, language, consent, key, delivery])
    await session.flush()
    history = {
        str(change_id)
        for change_id in await session.scalars(
            select(ApplicationStatusChange.id).where(
                ApplicationStatusChange.application_id == application.id
            )
        )
    }
    return {
        "companies.json": {str(application.company_id)},
        "applications.json": {str(application.id)},
        "application_status_changes.json": history,
        "interviews.json": {str(interview.id)},
        "reminders.json": {str(reminder.id)},
        "documents.json": {str(ready.id), str(pending.id)},
        "profiles.json": {str(profile.id)},
        "profile_entries.json": {str(entry.id)},
        "profile_entry_bullets.json": {str(bullet.id) for bullet in entry.bullets},
        "profile_skills.json": {str(skill.id)},
        "profile_languages.json": {str(language.id)},
        "ai_proposals.json": {str(proposal.id)},
        "ai_consents.json": {str(consent.id)},
        "ai_provider_keys.json": {str(key.id)},
    }


def _service(
    session: AsyncSession, *users: CurrentUser, root: Path | None = None
) -> AccountExportService:
    emails = {u.supertokens_user_id: f"{u.id}@example.com" for u in users}
    storage = LocalFileStorage(root or Path("/nonexistent"))
    return AccountExportService(session, storage, identities=FakeIdentities(emails))


async def _chunks(data: bytes) -> AsyncIterator[bytes]:
    yield data


async def _zip(
    service: AccountExportService, user: CurrentUser
) -> tuple[zipfile.ZipFile, int]:
    """El `.zip` entero y en cuántos trozos llegó."""
    snapshot = await service.snapshot(user, now=NOW)
    parts = [chunk async for chunk in service.zip_stream(snapshot)]
    archive = zipfile.ZipFile(io.BytesIO(b"".join(parts)))
    assert archive.testzip() is None
    return archive, len([part for part in parts if part])


@pytest.mark.asyncio
async def test_exports_every_table_and_only_this_account(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
) -> None:
    mine = await _fill(db_session, user)
    theirs = await _fill(db_session, other_user)

    snapshot = await _service(db_session, user, other_user).snapshot(user, now=NOW)

    expected_files = {table_file(table) for table in EXPORTED_TABLES}
    assert set(snapshot.json_files) == expected_files
    for file, ids in mine.items():
        exported = {row["id"] for row in snapshot.json_files[file]}
        assert exported == ids, file
        assert exported.isdisjoint(theirs[file]), f"{file}: datos de otra cuenta"


@pytest.mark.asyncio
async def test_account_file(db_session: AsyncSession, user: CurrentUser) -> None:
    snapshot = await _service(db_session, user).snapshot(user, now=NOW)

    account = snapshot.json_files["account.json"]
    assert account["format_version"] == FORMAT_VERSION
    assert account["exported_at"] == NOW.isoformat()
    assert account["email"] == f"{user.id}@example.com"
    assert account["account"]["id"] == str(user.id)
    assert "supertokens_user_id" not in account["account"]
    assert "notify_reminder_due" in account["account"]


@pytest.mark.asyncio
async def test_never_exports_secrets_or_internal_ids(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    await _fill(db_session, user)

    snapshot = await _service(db_session, user).snapshot(user, now=NOW)

    [key] = snapshot.json_files["ai_provider_keys.json"]
    assert set(key) == {
        "id",
        "provider",
        "model",
        "validated_at",
        "created_at",
        "updated_at",
    }
    dump = json.dumps(snapshot.json_files)
    assert CIPHERTEXT.decode() not in dump
    assert CIPHERTEXT.hex() not in dump
    assert LAST4 not in dump
    assert user.supertokens_user_id not in dump
    assert "storage_key" not in dump
    assert f"users/{user.id}/" not in dump
    # El registro de avisos enviados no es un dato que aportara la persona.
    assert "2026-W43" not in dump


@pytest.mark.asyncio
async def test_lists_only_the_pdfs_that_exist(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    ready = await make_document(db_session, user.id, name="CV Ana.pdf")
    await make_document(
        db_session,
        user.id,
        origin="generated",
        status="pending",
        storage_key=None,
        size_bytes=None,
        sha256=None,
        template="classic",
        language="es",
        content={"profile": {}},
    )

    snapshot = await _service(db_session, user).snapshot(user, now=NOW)

    assert [(f.path, f.storage_key) for f in snapshot.documents] == [
        (f"documents/{ready.id}-CV Ana.pdf", ready.storage_key)
    ]


@pytest.mark.asyncio
async def test_generated_documents_keep_their_snapshot(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    await make_document(
        db_session,
        user.id,
        origin="generated",
        status="pending",
        storage_key=None,
        size_bytes=None,
        sha256=None,
        template="classic",
        language="es",
        content={"profile": {"full_name": "Ana"}},
    )

    snapshot = await _service(db_session, user).snapshot(user, now=NOW)

    [document] = snapshot.json_files["documents.json"]
    assert document["content"] == {"profile": {"full_name": "Ana"}}


@pytest.mark.asyncio
async def test_a_user_without_row_is_not_found(db_session: AsyncSession) -> None:
    ghost = CurrentUser(id=uuid.uuid4(), supertokens_user_id="st-ghost")

    with pytest.raises(NotFoundError):
        await _service(db_session, ghost).snapshot(ghost, now=NOW)


@pytest.mark.asyncio
async def test_zip_has_every_json_the_pdfs_and_a_readme(
    db_session: AsyncSession, user: CurrentUser, tmp_path: Path
) -> None:
    storage = LocalFileStorage(tmp_path)
    first = await make_document(db_session, user.id, name="CV Ana.pdf")
    second = await make_document(db_session, user.id, name="CV Ana.pdf")
    await storage.put(first.storage_key or "", _chunks(b"%PDF-1 uno"))
    await storage.put(second.storage_key or "", _chunks(b"%PDF-1 dos"))

    archive, _ = await _zip(_service(db_session, user, root=tmp_path), user)

    names = set(archive.namelist())
    assert {table_file(table) for table in EXPORTED_TABLES} <= names
    # Mismo nombre visible, dos ficheros: el id delante evita que choquen.
    assert archive.read(f"documents/{first.id}-CV Ana.pdf") == b"%PDF-1 uno"
    assert archive.read(f"documents/{second.id}-CV Ana.pdf") == b"%PDF-1 dos"
    account = json.loads(archive.read("account.json"))
    assert account["email"] == f"{user.id}@example.com"
    readme = archive.read("README.txt").decode()
    assert "format_version 1" in readme
    assert "no estaban en el servidor" not in readme


@pytest.mark.asyncio
async def test_a_missing_pdf_is_skipped_and_reported(
    db_session: AsyncSession, user: CurrentUser, tmp_path: Path
) -> None:
    # Borrado entre la lectura de la BD y la copia: el resto sale igual.
    gone = await make_document(db_session, user.id, name="perdido.pdf")

    archive, _ = await _zip(_service(db_session, user, root=tmp_path), user)

    assert not [name for name in archive.namelist() if name.startswith("documents/")]
    assert f"documents/{gone.id}-perdido.pdf" in archive.read("README.txt").decode()


@pytest.mark.asyncio
async def test_the_zip_is_sent_in_parts(
    db_session: AsyncSession, user: CurrentUser, tmp_path: Path
) -> None:
    # Por trozos y no de una vez: un PDF grande no se junta entero en memoria.
    storage = LocalFileStorage(tmp_path)
    document = await make_document(db_session, user.id)
    big = (b"%PDF-1 " + bytes(range(256)) * 4096) * 4
    await storage.put(document.storage_key or "", _chunks(big))

    archive, parts = await _zip(_service(db_session, user, root=tmp_path), user)

    assert archive.read(f"documents/{document.id}-cv.pdf") == big
    assert parts > len(EXPORTED_TABLES) + 2
