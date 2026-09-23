from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company


@pytest.mark.asyncio
async def test_create_application_returns_full_resource(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id, "Acme")

    response = await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(company.id),
            "position_title": "Backend Developer",
            "work_mode": "remote",
            "source": "linkedin",
            "applied_at": "2026-09-15",
            "salary_min": 40000,
            "salary_max": 50000,
            "salary_currency": "EUR",
            "job_url": "https://acme.example/jobs/1",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company"] == {"id": str(company.id), "name": "Acme"}
    assert body["status"] == "applied"
    assert body["origin"] == "manual"
    assert body["salary_currency"] == "EUR"
    assert body["archived_at"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "interviewing"},
        {"salary_min": 60000, "salary_max": 50000},
        {"position_title": "  "},
        {"job_url": "javascript:alert(1)"},
        {"salary_currency": "EURO"},
        {"work_mode": "sometimes"},
    ],
    ids=[
        "status_not_initial",
        "inverted_salary",
        "blank_title",
        "url_without_http",
        "bad_currency",
        "unknown_work_mode",
    ],
)
async def test_invalid_application_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    overrides: dict[str, object],
):
    company = await make_company(db_session, user.id)
    payload = {"company_id": str(company.id), "position_title": "Dev"} | overrides

    response = await client.post("/api/v1/applications", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_ignores_status_field(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Invariante 3: el estado no se cambia con PATCH.
    application = await make_application(db_session, user.id)

    response = await client.patch(
        f"/api/v1/applications/{application.id}",
        json={"status": "offer", "notes": "x"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_patch_error_has_stable_code(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, salary_min=40000, salary_max=50000
    )

    response = await client.patch(
        f"/api/v1/applications/{application.id}", json={"salary_min": 90000}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "salary_range_invalid"


@pytest.mark.asyncio
async def test_archive_and_unarchive(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    url = f"/api/v1/applications/{application.id}"

    archived = await client.post(f"{url}/archive")
    active_list = await client.get("/api/v1/applications")
    archived_list = await client.get(
        "/api/v1/applications", params={"archived": "archived"}
    )
    unarchived = await client.post(f"{url}/unarchive")

    assert archived.json()["archived_at"] is not None
    assert active_list.json()["total"] == 0
    assert archived_list.json()["total"] == 1
    assert unarchived.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_list_filters_with_repeated_query_params(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, position_title="A", status="applied")
    await make_application(
        db_session, user.id, position_title="B", status="saved", applied_at=None
    )
    await make_application(
        db_session,
        user.id,
        position_title="C",
        status="screening",
        applied_at=date(2026, 9, 2),
    )

    response = await client.get(
        "/api/v1/applications",
        params=[
            ("status", "saved"),
            ("status", "screening"),
            ("sort_by", "position_title"),
            ("order", "asc"),
        ],
    )

    assert [item["position_title"] for item in response.json()["items"]] == ["B", "C"]


@pytest.mark.asyncio
async def test_list_rejects_inverted_date_range(client: AsyncClient):
    response = await client.get(
        "/api/v1/applications",
        params={"applied_from": "2026-09-10", "applied_to": "2026-09-01"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_application(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)

    deleted = await client.delete(f"/api/v1/applications/{application.id}")
    again = await client.get(f"/api/v1/applications/{application.id}")

    assert deleted.status_code == 204
    assert again.status_code == 404


@pytest.mark.asyncio
async def test_export_returns_a_csv_attachment(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, position_title="Backend Developer")

    response = await client.get("/api/v1/applications/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="applications.csv"'
    )
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("position_title,company,status")
    assert "Backend Developer" in lines[1]


@pytest.mark.asyncio
async def test_export_does_not_leak_another_users_applications(
    client: AsyncClient, db_session: AsyncSession, other_user: CurrentUser
):
    await make_application(db_session, other_user.id, position_title="Ajena")

    response = await client.get("/api/v1/applications/export")

    assert len(response.text.strip().splitlines()) == 1  # solo la cabecera
