"""Aislamiento entre usuarios (arquitectura §7, pruebas T2 y T3).

El usuario B intenta leer, editar, archivar y borrar los recursos de A por su id.
Todas las operaciones deben responder 404, igual que si el recurso no existiera
(decisión A10), y los datos de A no deben cambiar.
"""

import re
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.application import Application
from app.models.company import Company
from app.schemas.user import CurrentUser
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
)

# Toda operación con un id de recurso en la ruta. test_every_id_route_is_covered
# falla si aparece una nueva en el OpenAPI y no está aquí.
ID_OPERATIONS: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/api/v1/companies/{company_id}", None),
    ("PATCH", "/api/v1/companies/{company_id}", {"name": "Hackeada"}),
    ("DELETE", "/api/v1/companies/{company_id}", None),
    ("GET", "/api/v1/applications/{application_id}", None),
    ("PATCH", "/api/v1/applications/{application_id}", {"position_title": "Hackeada"}),
    ("DELETE", "/api/v1/applications/{application_id}", None),
    ("POST", "/api/v1/applications/{application_id}/archive", None),
    ("POST", "/api/v1/applications/{application_id}/unarchive", None),
    ("GET", "/api/v1/applications/{application_id}/status-changes", None),
    (
        "POST",
        "/api/v1/applications/{application_id}/status-changes",
        {"to_status": "applied"},
    ),
    ("DELETE", "/api/v1/applications/{application_id}/status-changes/last", None),
    ("GET", "/api/v1/applications/{application_id}/interviews", None),
    (
        "POST",
        "/api/v1/applications/{application_id}/interviews",
        {"scheduled_at": "2026-10-01T10:00:00Z"},
    ),
    (
        "PATCH",
        "/api/v1/applications/{application_id}/interviews/{interview_id}",
        {"notes": "Hackeada"},
    ),
    ("DELETE", "/api/v1/applications/{application_id}/interviews/{interview_id}", None),
    ("POST", "/api/v1/reminders/{reminder_id}/complete", None),
    ("POST", "/api/v1/reminders/{reminder_id}/dismiss", None),
]


def test_every_id_route_is_covered():
    documented = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if re.search(r"\{\w+_id\}", path)
        for method in operations
    }
    covered = {(method, path) for method, path, _ in ID_OPERATIONS}

    assert documented == covered


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "path", "body"), ID_OPERATIONS)
async def test_other_user_gets_404_and_nothing_changes(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
    method: str,
    path: str,
    body: dict[str, Any] | None,
):
    company = await make_company(db_session, user.id, "Acme")
    application = await make_application(
        db_session, user.id, company, position_title="Original"
    )
    interview = await make_interview(db_session, application, notes="Original")
    reminder = await make_reminder(
        db_session, user.id, application_id=application.id, title="Original"
    )
    url = path.format(
        company_id=company.id,
        application_id=application.id,
        interview_id=interview.id,
        reminder_id=reminder.id,
    )

    as_user(other_user)
    response = await client.request(method, url, json=body)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"

    await db_session.refresh(company)
    await db_session.refresh(application)
    await db_session.refresh(interview)
    await db_session.refresh(reminder)
    assert company.name == "Acme"
    assert application.position_title == "Original"
    assert application.archived_at is None
    assert interview.notes == "Original"
    assert reminder.status == "pending"


@pytest.mark.asyncio
async def test_lists_never_include_other_users_data(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    await make_application(db_session, user.id)

    as_user(other_user)
    companies = await client.get("/api/v1/companies")
    applications = await client.get("/api/v1/applications", params={"archived": "all"})

    assert companies.json()["total"] == 0
    assert applications.json()["total"] == 0


@pytest.mark.asyncio
async def test_filtering_by_another_users_company_returns_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    others_application = await make_application(db_session, other_user.id)

    response = await client.get(
        "/api/v1/applications",
        params={"company_id": str(others_application.company_id)},
    )

    assert response.json()["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_cannot_link_an_application_to_another_users_company(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    operation: str,
):
    # T3: ni al crear ni al editar.
    others_company = await make_company(db_session, other_user.id, "Ajena")

    if operation == "create":
        response = await client.post(
            "/api/v1/applications",
            json={"company_id": str(others_company.id), "position_title": "Dev"},
        )
    else:
        own = await make_application(db_session, user.id)
        response = await client.patch(
            f"/api/v1/applications/{own.id}",
            json={"company_id": str(others_company.id)},
        )

    assert response.status_code == 404

    linked = [
        application
        for application in (
            await db_session.execute(
                Application.__table__.select().where(
                    Application.company_id == others_company.id
                )
            )
        ).all()
    ]
    assert linked == []
    assert isinstance(others_company, Company)


@pytest.mark.asyncio
async def test_reminder_list_never_includes_other_users_data(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    await make_reminder(db_session, user.id)

    as_user(other_user)
    response = await client.get("/api/v1/reminders", params={"status": "all"})

    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_cannot_link_a_reminder_to_another_users_application(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    # T3: crear un recordatorio apuntando a la solicitud de otro usuario.
    others_application = await make_application(db_session, other_user.id)

    response = await client.post(
        "/api/v1/reminders",
        json={
            "title": "x",
            "due_at": "2026-10-01T10:00:00Z",
            "application_id": str(others_application.id),
        },
    )

    assert response.status_code == 404
