"""Ficheros huérfanos y borrado de la cuenta con sus ficheros (ficheros §5 y §8:
D6 y D11; RNF-41)."""

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents import ORPHAN_GRACE, DocumentKind, storage_key, user_prefix
from app.infra.storage import LocalFileStorage
from app.jobs.files import file_cron_jobs, sweep_orphan_files
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser
from app.services.account_service import AccountService
from app.services.document_service import DocumentService
from app.services.orphan_file_service import OrphanFileService
from tests.factories import make_document
from tests.pdf_helpers import make_pdf

NOW = datetime(2026, 10, 1, 4, 15, tzinfo=UTC)


async def _chunks(content: bytes) -> AsyncIterator[bytes]:
    yield content


async def _write(storage: LocalFileStorage, key: str, age: timedelta) -> Path:
    await storage.put(key, _chunks(b"%PDF-1.4"))
    path = Path(storage._root) / key
    when = (NOW - age).timestamp()
    os.utime(path, (when, when))
    return path


@pytest.mark.asyncio
async def test_sweep_deletes_old_orphans_and_keeps_files_with_a_row(
    db_session: AsyncSession, user: CurrentUser, tmp_path: Path
):
    storage = LocalFileStorage(tmp_path)
    kept = await make_document(db_session, user.id)
    assert kept.storage_key is not None
    with_row = await _write(storage, kept.storage_key, timedelta(days=3))
    orphan = await _write(
        storage, storage_key(user.id, uuid.uuid4()), ORPHAN_GRACE + timedelta(minutes=1)
    )
    # Una subida en curso: el fichero ya está escrito y su fila aún no.
    in_flight = await _write(
        storage, storage_key(user.id, uuid.uuid4()), ORPHAN_GRACE - timedelta(minutes=1)
    )

    result = await OrphanFileService(db_session, storage).sweep(NOW)

    assert result.files == 1
    assert with_row.exists()
    assert not orphan.exists()
    assert in_flight.exists()


@pytest.mark.asyncio
async def test_a_failed_commit_leaves_an_orphan_that_the_sweep_removes_later(
    db_session: AsyncSession,
    user: CurrentUser,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # D6: falla el commit después de escribir el fichero. Queda un fichero sin
    # fila (nunca una fila sin fichero), y el barrido lo borra pasada la hora y no
    # antes.
    storage = LocalFileStorage(tmp_path)

    async def broken_commit() -> None:
        raise ConnectionError("la BD se cayó")

    monkeypatch.setattr(db_session, "commit", broken_commit)
    with pytest.raises(ConnectionError):
        await DocumentService(db_session, storage).upload(
            user.id, kind=DocumentKind.CV, name="cv.pdf", body=_chunks(make_pdf())
        )
    monkeypatch.undo()
    await db_session.rollback()
    [written] = [stored async for stored in storage.iter_files()]
    written_at = written.modified_at

    too_soon = await OrphanFileService(db_session, storage).sweep(
        written_at + ORPHAN_GRACE - timedelta(seconds=1)
    )
    later = await OrphanFileService(db_session, storage).sweep(
        written_at + ORPHAN_GRACE + timedelta(seconds=1)
    )

    assert too_soon.files == 0
    assert later.files == 1
    assert [stored async for stored in storage.iter_files()] == []


@pytest.mark.asyncio
async def test_sweep_also_removes_old_temporaries(
    db_session: AsyncSession, tmp_path: Path
):
    storage = LocalFileStorage(tmp_path)
    temporary = tmp_path / ".tmp" / "murio.part"
    temporary.parent.mkdir()
    temporary.write_bytes(b"a medias")
    when = (NOW - timedelta(days=1)).timestamp()
    os.utime(temporary, (when, when))

    result = await OrphanFileService(db_session, storage).sweep(NOW)

    assert result.temporaries == 1
    assert not temporary.exists()


def test_the_orphan_sweep_runs_daily_with_or_without_email() -> None:
    [job] = file_cron_jobs()

    assert job.function is sweep_orphan_files
    assert job.cron == "15 4 * * *"


# --- Borrar la cuenta borra sus ficheros (RNF-41, D11) -------------------------


class RecordingIdentities(IdentityRepository):
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, supertokens_user_id: str) -> None:
        self.deleted.append(supertokens_user_id)


@pytest.mark.asyncio
async def test_deleting_the_account_deletes_its_files_and_nobody_elses(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser, tmp_path: Path
):
    storage = LocalFileStorage(tmp_path)
    own = await _write(storage, storage_key(user.id, uuid.uuid4()), timedelta())
    others = await _write(
        storage, storage_key(other_user.id, uuid.uuid4()), timedelta()
    )
    identities = RecordingIdentities()

    await AccountService(db_session, storage, identities=identities).delete_account(
        user
    )

    assert not own.exists()
    assert not (tmp_path / user_prefix(user.id)).exists()
    assert others.exists()
    assert identities.deleted == [user.supertokens_user_id]


@pytest.mark.asyncio
async def test_if_deleting_the_files_fails_the_account_is_still_deleted(
    db_session: AsyncSession,
    user: CurrentUser,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # D11: los ficheros se borran después del commit. Si falla, quedan huérfanos
    # que limpia el barrido; la cuenta y la identidad se borran igual.
    storage = LocalFileStorage(tmp_path)
    own = await _write(storage, storage_key(user.id, uuid.uuid4()), timedelta(days=1))

    async def broken_delete_prefix(self: LocalFileStorage, prefix: str) -> None:
        raise OSError("disco")

    monkeypatch.setattr(LocalFileStorage, "delete_prefix", broken_delete_prefix)
    identities = RecordingIdentities()

    await AccountService(db_session, storage, identities=identities).delete_account(
        user
    )
    monkeypatch.undo()

    assert identities.deleted == [user.supertokens_user_id]
    assert own.exists()
    result = await OrphanFileService(db_session, storage).sweep(NOW)
    assert result.files == 1
    assert not own.exists()
