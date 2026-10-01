"""Documentos en las solicitudes y descripción de la oferta (RF-27, RF-28, RF-92,
RF-93; ficheros §8, D5)."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.application import MAX_JOB_DESCRIPTION_LENGTH
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company, make_document

APPLICATIONS = "/api/v1/applications"
DOCUMENTS = "/api/v1/documents"


@pytest.mark.asyncio
async def test_create_with_job_description_cv_and_cover_letter(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    cv = await make_document(db_session, user.id, kind="cv", name="cv.pdf")
    letter = await make_document(
        db_session, user.id, kind="cover_letter", name="carta.pdf"
    )

    response = await client.post(
        APPLICATIONS,
        json={
            "company_id": str(company.id),
            "position_title": "Backend",
            "job_description": "  Buscamos backend con Python.  ",
            "cv_document_id": str(cv.id),
            "cover_letter_document_id": str(letter.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_description"] == "Buscamos backend con Python."
    assert body["cv_document"]["id"] == str(cv.id)
    assert body["cv_document"]["name"] == "cv.pdf"
    assert body["cover_letter_document"]["kind"] == "cover_letter"


@pytest.mark.asyncio
async def test_the_list_does_not_carry_the_description_or_the_documents(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Hasta 20 000 caracteres por solicitud: solo viajan en el detalle.
    cv = await make_document(db_session, user.id)
    await make_application(
        db_session, user.id, job_description="x" * 1000, cv_document_id=cv.id
    )

    item = (await client.get(APPLICATIONS)).json()["items"][0]

    assert "job_description" not in item
    assert "cv_document" not in item


@pytest.mark.asyncio
async def test_patch_assigns_and_clears_documents(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    cv = await make_document(db_session, user.id)

    assigned = await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"cv_document_id": str(cv.id)}
    )
    untouched = await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"notes": "hola"}
    )
    cleared = await client.patch(
        f"{APPLICATIONS}/{application.id}",
        json={"cv_document_id": None, "job_description": ""},
    )

    assert assigned.json()["cv_document"]["id"] == str(cv.id)
    # Solo cambia lo enviado.
    assert untouched.json()["cv_document"]["id"] == str(cv.id)
    assert cleared.json()["cv_document"] is None
    assert cleared.json()["job_description"] is None


@pytest.mark.asyncio
async def test_a_cv_cannot_be_sent_as_a_cover_letter(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Una FK no puede comprobar el tipo (es una columna de la otra fila): lo hace
    # el service.
    application = await make_application(db_session, user.id)
    cv = await make_document(db_session, user.id, kind="cv")

    response = await client.patch(
        f"{APPLICATIONS}/{application.id}",
        json={"cover_letter_document_id": str(cv.id)},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "document_kind_mismatch"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fields",
    [
        {"status": "pending", "storage_key": None, "error_code": None},
        {"status": "failed", "storage_key": None, "error_code": "render_failed"},
    ],
)
async def test_a_cv_without_a_pdf_cannot_be_sent(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    fields: dict[str, str | None],
):
    # F14: uno que se está generando o que falló no tiene PDF. La interfaz solo
    # ofrece los `ready`; la API lo impone igual.
    application = await make_application(db_session, user.id)
    cv = await make_document(
        db_session,
        user.id,
        origin="generated",
        size_bytes=None,
        sha256=None,
        template="classic",
        language="es",
        content={"contact": {}},
        **fields,
    )

    response = await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"cv_document_id": str(cv.id)}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "document_not_ready"
    await db_session.refresh(application)
    assert application.cv_document_id is None


@pytest.mark.asyncio
async def test_another_users_document_is_a_404_and_nothing_changes(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    application = await make_application(db_session, user.id)
    foreign = await make_document(db_session, other_user.id)

    patched = await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"cv_document_id": str(foreign.id)}
    )
    missing = await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"cv_document_id": str(uuid.uuid4())}
    )

    assert patched.status_code == 404
    assert patched.json() == missing.json()
    await db_session.refresh(application)
    assert application.cv_document_id is None


@pytest.mark.asyncio
async def test_job_description_is_limited(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)

    response = await client.patch(
        f"{APPLICATIONS}/{application.id}",
        json={"job_description": "x" * (MAX_JOB_DESCRIPTION_LENGTH + 1)},
    )

    assert response.status_code == 422


# --- Desde el documento: usado en y borrado (RF-92, RF-93) ----------------------


@pytest.mark.asyncio
async def test_document_detail_lists_where_it_was_sent(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id, "Acme")
    cv = await make_document(db_session, user.id, kind="cv")
    letter = await make_document(db_session, user.id, kind="cover_letter")
    sent = await make_application(
        db_session,
        user.id,
        company,
        position_title="Backend",
        cv_document_id=cv.id,
        cover_letter_document_id=letter.id,
    )
    archived = await make_application(
        db_session,
        user.id,
        company,
        position_title="Antigua",
        cv_document_id=cv.id,
        archived_at=datetime.now(UTC),
    )
    await make_application(db_session, user.id, company, position_title="Sin CV")

    cv_detail = (await client.get(f"{DOCUMENTS}/{cv.id}")).json()
    letter_detail = (await client.get(f"{DOCUMENTS}/{letter.id}")).json()

    assert {
        (item["application_id"], item["used_as"], item["application_archived"])
        for item in cv_detail["used_in"]
    } == {(str(sent.id), "cv", False), (str(archived.id), "cv", True)}
    assert cv_detail["used_in"][0]["company_name"] == "Acme"
    assert [item["used_as"] for item in letter_detail["used_in"]] == ["cover_letter"]


@pytest.mark.asyncio
async def test_a_document_in_use_cannot_be_deleted_but_can_be_archived(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # D5: borrarlo perdería qué se envió a quién. Archivado, sigue asociado.
    cv = await make_document(db_session, user.id)
    application = await make_application(db_session, user.id, cv_document_id=cv.id)

    deleted = await client.delete(f"{DOCUMENTS}/{cv.id}")
    archived = await client.post(f"{DOCUMENTS}/{cv.id}/archive")
    detail = (await client.get(f"{APPLICATIONS}/{application.id}")).json()

    assert deleted.status_code == 409
    assert deleted.json()["code"] == "document_in_use"
    assert deleted.json()["applications"] == 1
    assert archived.status_code == 200
    assert detail["cv_document"]["id"] == str(cv.id)
    assert detail["cv_document"]["archived_at"] is not None


@pytest.mark.asyncio
async def test_once_unassigned_the_document_can_be_deleted(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    cv = await make_document(db_session, user.id)
    application = await make_application(db_session, user.id, cv_document_id=cv.id)

    await client.patch(
        f"{APPLICATIONS}/{application.id}", json={"cv_document_id": None}
    )
    response = await client.delete(f"{DOCUMENTS}/{cv.id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_usage_of_another_users_document_is_a_404(
    client: AsyncClient,
    db_session: AsyncSession,
    other_user: CurrentUser,
):
    foreign = await make_document(db_session, other_user.id)

    response = await client.get(f"{DOCUMENTS}/{foreign.id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_the_library_says_how_many_applications_each_document_was_sent_in(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    cv = await make_document(db_session, user.id, kind="cv", name="cv.pdf")
    letter = await make_document(db_session, user.id, kind="cover_letter")
    unused = await make_document(db_session, user.id, name="sin-usar.pdf")
    await make_application(
        db_session, user.id, cv_document_id=cv.id, cover_letter_document_id=letter.id
    )
    # Las archivadas cuentan: el documento sigue enviado en ellas.
    await make_application(
        db_session, user.id, cv_document_id=cv.id, archived_at=datetime.now(UTC)
    )
    # Un documento del otro usuario con el mismo uso no afecta al recuento.
    foreign = await make_document(db_session, other_user.id)
    await make_application(db_session, other_user.id, cv_document_id=foreign.id)

    items = (await client.get(DOCUMENTS)).json()["items"]
    counts = {item["id"]: item["applications_count"] for item in items}

    assert counts == {str(cv.id): 2, str(letter.id): 1, str(unused.id): 0}
