"""Límites por usuario (límites y abuso §1: L1, L2 y L3; RF-140…143)."""

import re
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import LimitReachedError
from app.domain.limits import (
    LIMIT_RULES,
    LimitKey,
    LimitRule,
    keys_allowing_unlimited,
)
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService
from app.services.limit_service import LimitService, LimitUsage
from tests.factories import make_application, make_company, make_reminder


def _by_key(usage: list[LimitUsage], key: LimitKey) -> LimitUsage:
    return next(item for item in usage if item.key == key)


@pytest.mark.asyncio
async def test_usage_counts_real_rows_of_this_user_only(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    company = await make_company(db_session, user.id)
    await make_application(db_session, user.id, company=company)
    # Las archivadas también cuentan: siguen ocupando sitio.
    await make_application(
        db_session, user.id, company=company, archived_at=datetime.now(UTC)
    )
    await make_reminder(db_session, user.id)
    await make_reminder(db_session, user.id, status="done")
    await make_application(db_session, other_user.id)

    usage = await LimitService(db_session).usage(user.id)

    assert _by_key(usage, LimitKey.APPLICATIONS).used == 2
    assert _by_key(usage, LimitKey.COMPANIES).used == 1
    # Los recordatorios cuentan en cualquier estado (decisión 0011).
    assert _by_key(usage, LimitKey.REMINDERS).used == 2
    applications = _by_key(usage, LimitKey.APPLICATIONS)
    assert applications.limit == settings.limit_applications
    assert applications.remaining == settings.limit_applications - 2
    assert applications.renews is False


@pytest.mark.asyncio
async def test_usage_follows_a_cascade_delete(
    db_session: AsyncSession, user: CurrentUser
):
    # L2: el consumo se calcula, no se cuenta. Borrar una solicitud se lleva por
    # delante sus recordatorios (ON DELETE CASCADE) sin pasar por ningún contador,
    # y el uso sigue cuadrando.
    application = await make_application(db_session, user.id)
    await make_reminder(db_session, user.id, application_id=application.id)
    service = LimitService(db_session)
    before = await service.usage(user.id)

    await ApplicationService(db_session).delete(user.id, application.id)
    after = await service.usage(user.id)

    assert _by_key(before, LimitKey.REMINDERS).used == 1
    assert _by_key(after, LimitKey.REMINDERS).used == 0
    assert _by_key(after, LimitKey.APPLICATIONS).used == 0


@pytest.mark.asyncio
async def test_override_applies_to_that_user_only(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # L1 (RF-143).
    service = LimitService(db_session)

    await service.set_override(user.id, LimitKey.COMPANIES, 3)

    assert await service.limit_for(user.id, LimitKey.COMPANIES) == 3
    assert (
        await service.limit_for(other_user.id, LimitKey.COMPANIES)
        == settings.limit_companies
    )
    usage = await service.usage(user.id)
    assert _by_key(usage, LimitKey.COMPANIES).overridden is True
    assert _by_key(usage, LimitKey.APPLICATIONS).overridden is False


@pytest.mark.asyncio
async def test_clearing_an_override_returns_to_the_global_value(
    db_session: AsyncSession, user: CurrentUser
):
    service = LimitService(db_session)
    await service.set_override(user.id, LimitKey.COMPANIES, 3)
    await service.set_override(user.id, LimitKey.COMPANIES, 7)  # sustituye, no duplica

    assert await service.limit_for(user.id, LimitKey.COMPANIES) == 7
    await service.clear_override(user.id, LimitKey.COMPANIES)
    assert (
        await service.limit_for(user.id, LimitKey.COMPANIES) == settings.limit_companies
    )


@pytest.mark.asyncio
async def test_check_reports_limit_and_used(
    db_session: AsyncSession, user: CurrentUser
):
    # L3 (RF-142): el error dice cuál y cuánto.
    service = LimitService(db_session)
    await make_company(db_session, user.id)
    await make_company(db_session, user.id)
    await service.set_override(user.id, LimitKey.COMPANIES, 2)

    with pytest.raises(LimitReachedError) as error:
        await service.check(user.id, LimitKey.COMPANIES)

    assert error.value.code == "companies_limit_reached"
    assert error.value.extra == {"limit": 2, "used": 2}


@pytest.mark.asyncio
async def test_a_lowered_limit_blocks_creating_but_deletes_nothing(
    db_session: AsyncSession, user: CurrentUser
):
    service = LimitService(db_session)
    await make_company(db_session, user.id)
    await make_company(db_session, user.id)

    await service.set_override(user.id, LimitKey.COMPANIES, 1)
    usage = _by_key(await service.usage(user.id), LimitKey.COMPANIES)

    assert usage.used == 2
    assert usage.remaining == 0
    with pytest.raises(LimitReachedError):
        await service.check(user.id, LimitKey.COMPANIES)


@pytest.mark.asyncio
async def test_negative_override_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    with pytest.raises(ValueError):
        await LimitService(db_session).set_override(user.id, LimitKey.COMPANIES, -1)


@pytest.mark.asyncio
async def test_unlimited_never_blocks_and_only_for_that_account_and_limit(
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "limit_companies", 1)
    service = LimitService(db_session)
    await make_company(db_session, user.id)
    await make_company(db_session, user.id)
    await make_company(db_session, other_user.id)

    await service.set_override(user.id, LimitKey.COMPANIES, None)

    await service.check(user.id, LimitKey.COMPANIES, amount=1_000_000)
    companies = _by_key(await service.usage(user.id), LimitKey.COMPANIES)
    assert (companies.used, companies.limit, companies.remaining) == (2, None, None)
    assert companies.overridden is True
    # Los demás límites de la cuenta y las demás cuentas, intactos.
    assert await service.limit_for(user.id, LimitKey.APPLICATIONS) == (
        settings.limit_applications
    )
    with pytest.raises(LimitReachedError):
        await service.check(other_user.id, LimitKey.COMPANIES)


@pytest.mark.asyncio
async def test_limits_protecting_a_cost_cannot_be_unlimited(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    # Almacenamiento e IA (F13, F15) tendrán tope siempre: el service lo rechaza
    # para cualquier límite que no lo admita.
    monkeypatch.setitem(
        LIMIT_RULES,
        LimitKey.COMPANIES,
        LimitRule(error_code="companies_limit_reached", allows_unlimited=False),
    )

    with pytest.raises(ValueError, match="tiene que tener un límite"):
        await LimitService(db_session).set_override(user.id, LimitKey.COMPANIES, None)


@pytest.mark.asyncio
async def test_database_allows_unlimited_exactly_where_the_domain_does(
    db_session: AsyncSession,
):
    # La misma regla, impuesta también por la BD (CHECK de la migración). Si un
    # límite cambia de parecer en domain/limits.py sin migración, esto falla.
    definition = await db_session.scalar(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_user_limit_overrides_unlimited_only_where_allowed'"
        )
    )
    assert definition is not None
    allowed = set(re.findall(r"'(\w+)'", definition))
    assert allowed == {key.value for key in keys_allowing_unlimited()}
