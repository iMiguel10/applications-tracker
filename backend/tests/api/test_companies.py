import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company


@pytest.mark.asyncio
async def test_create_and_read_company(client: AsyncClient):
    created = await client.post(
        "/api/v1/companies",
        json={"name": "  Acme  ", "website": "https://acme.example", "location": ""},
    )

    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Acme"
    assert body["location"] is None  # "" se guarda como null
    assert body["applications_count"] == 0

    detail = await client.get(f"/api/v1/companies/{body['id']}")
    assert detail.json()["website"] == "https://acme.example"


@pytest.mark.asyncio
async def test_duplicate_name_returns_409_with_code(client: AsyncClient):
    await client.post("/api/v1/companies", json={"name": "Acme"})

    response = await client.post("/api/v1/companies", json={"name": "ACME"})

    assert response.status_code == 409
    assert response.json()["code"] == "company_name_taken"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"name": ""}, {"name": "x" * 201}, {"name": "Acme", "website": "acme.example"}],
    ids=["empty_name", "long_name", "website_without_scheme"],
)
async def test_invalid_company_is_422(client: AsyncClient, payload: dict[str, str]):
    response = await client.post("/api/v1/companies", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_null_clears_an_optional_field(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(
        db_session, user.id, "Acme", location="Madrid", notes="n"
    )

    response = await client.patch(
        f"/api/v1/companies/{company.id}", json={"location": None}
    )

    assert response.status_code == 200
    assert response.json()["location"] is None
    assert response.json()["notes"] == "n"


@pytest.mark.asyncio
async def test_delete_company_in_use_is_409(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    await make_application(db_session, user.id, company)

    response = await client.delete(f"/api/v1/companies/{company.id}")

    assert response.status_code == 409
    assert response.json()["code"] == "company_in_use"


@pytest.mark.asyncio
async def test_delete_unused_company(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)

    deleted = await client.delete(f"/api/v1/companies/{company.id}")
    again = await client.get(f"/api/v1/companies/{company.id}")

    assert deleted.status_code == 204
    assert again.status_code == 404


@pytest.mark.asyncio
async def test_list_searches_and_sorts_by_applications_count(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    busy = await make_company(db_session, user.id, "Busy Corp")
    await make_company(db_session, user.id, "Quiet Corp")
    await make_company(db_session, user.id, "Other")
    await make_application(db_session, user.id, busy)

    response = await client.get(
        "/api/v1/companies",
        params={"q": "corp", "sort_by": "applications_count", "order": "desc"},
    )

    body = response.json()
    assert body["total"] == 2
    assert [c["name"] for c in body["items"]] == ["Busy Corp", "Quiet Corp"]
