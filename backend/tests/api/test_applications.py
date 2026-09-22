import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_application_returns_201_with_generated_fields(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/applications",
        json={"position_title": "Backend Developer", "company_name": "Acme"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["position_title"] == "Backend Developer"
    assert body["company_name"] == "Acme"
    assert body["id"]
    assert body["created_at"]


@pytest.mark.asyncio
async def test_create_application_trims_whitespace(client: AsyncClient):
    response = await client.post(
        "/api/v1/applications",
        json={"position_title": "  Backend Developer  ", "company_name": " Acme "},
    )

    assert response.status_code == 201
    assert response.json()["position_title"] == "Backend Developer"
    assert response.json()["company_name"] == "Acme"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"position_title": "   ", "company_name": "Acme"},
        {"position_title": "Backend Developer"},
        {"position_title": "x" * 201, "company_name": "Acme"},
    ],
    ids=["blank_title", "missing_company", "title_too_long"],
)
async def test_create_application_rejects_invalid_payload(
    client: AsyncClient, payload: dict[str, str]
):
    response = await client.post("/api/v1/applications", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_applications_returns_newest_first_with_pagination(
    client: AsyncClient,
):
    for title in ("Primero", "Segundo"):
        await client.post(
            "/api/v1/applications",
            json={"position_title": title, "company_name": "Acme"},
        )

    response = await client.get("/api/v1/applications", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["pages"] == 2
    assert [item["position_title"] for item in body["items"]] == ["Segundo"]


@pytest.mark.asyncio
async def test_list_applications_rejects_limit_over_100(client: AsyncClient):
    response = await client.get("/api/v1/applications", params={"limit": 101})

    assert response.status_code == 422
