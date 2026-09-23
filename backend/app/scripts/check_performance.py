"""Valida los presupuestos de rendimiento RNF-10 (listado, p95 < 300 ms) y
RNF-11 (dashboard, p95 < 500 ms) con ~2000 solicitudes por usuario, el volumen
que fija la especificación (§9).

    docker compose -f compose.test.yml run --rm api-test python -m app.scripts.check_performance

Se ejecuta solo contra la base de test (`ENV=test`): rehúsa arrancar contra
cualquier otra, para no poder sembrar datos de prueba en una base real por
error. No se ejecuta en CI (es lento y necesita volumen de datos a propósito):
es un chequeo manual para revalidar cuando convenga, no una prueba de cada push.
Siembra sus propios datos y los borra al terminar, haya ido bien o mal.
"""

import asyncio
import statistics
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.domain.application_status import ApplicationStatus
from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.repositories.application_repository import (
    ApplicationFilters,
    ApplicationRepository,
)
from app.services.dashboard_service import DashboardService

APPLICATIONS_PER_USER = 2000
ITERATIONS = 20
LISTING_BUDGET_MS = 300
DASHBOARD_BUDGET_MS = 500


async def _seed(
    session: AsyncSession, user_id: uuid.UUID, company_id: uuid.UUID
) -> None:
    statuses = list(ApplicationStatus)
    now = datetime.now(UTC)
    rows = [
        {
            "user_id": user_id,
            "company_id": company_id,
            "position_title": f"Puesto de prueba {i}",
            "status": statuses[i % len(statuses)].value,
            "applied_at": date(2024, 1, 1) + timedelta(days=i % 900),
            "last_activity_at": now - timedelta(days=i % 400),
        }
        for i in range(APPLICATIONS_PER_USER)
    ]
    await session.execute(insert(Application), rows)
    # Sin esto, el planificador decide sobre estadísticas de una tabla que cree
    # vacía (o con las de antes del seed): el tiempo medido no sería el real.
    await session.execute(text("ANALYZE applications"))


def _p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=100)[93]


async def _measure(fn: Callable[[], Awaitable[object]]) -> float:
    start = time.perf_counter()
    await fn()
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    if settings.env != "test":
        raise SystemExit(
            f"ENV={settings.env}, no 'test'. Este script siembra y borra 2000 "
            "solicitudes: solo se ejecuta contra la base de test."
        )

    engine = create_async_engine(settings.database_url)
    user_id: uuid.UUID | None = None
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(supertokens_user_id=f"perf-check-{uuid.uuid4()}")
            session.add(user)
            await session.flush()
            user_id = user.id
            company = Company(user_id=user.id, name="Perf Co")
            session.add(company)
            await session.flush()

            await _seed(session, user.id, company.id)
            await session.commit()

            applications = ApplicationRepository(session)
            dashboard = DashboardService(session)

            listing_samples = [
                await _measure(
                    lambda: applications.list(
                        user.id,
                        ApplicationFilters(),
                        page=1,
                        limit=20,
                        sort_by="applied_at",
                        descending=True,
                    )
                )
                for _ in range(ITERATIONS)
            ]
            dashboard_samples = [
                await _measure(lambda: dashboard.get(user.id))
                for _ in range(ITERATIONS)
            ]

            listing_p95 = _p95(listing_samples)
            dashboard_p95 = _p95(dashboard_samples)
            print(
                f"Listado (RNF-10):   p95 = {listing_p95:7.1f} ms  (presupuesto {LISTING_BUDGET_MS} ms)"
            )
            print(
                f"Dashboard (RNF-11): p95 = {dashboard_p95:7.1f} ms  (presupuesto {DASHBOARD_BUDGET_MS} ms)"
            )

            assert listing_p95 < LISTING_BUDGET_MS, "RNF-10 incumplido"
            assert dashboard_p95 < DASHBOARD_BUDGET_MS, "RNF-11 incumplido"
    finally:
        # Limpieza siempre, incluso si algo de arriba falla: nunca deja los 2000
        # registros de prueba en la base. Conexión propia porque la de arriba
        # puede haber quedado en un estado inválido tras un error. ON DELETE
        # CASCADE se lleva la empresa y las solicitudes.
        if user_id is not None:
            async with AsyncSession(engine) as cleanup:
                await cleanup.execute(delete(User).where(User.id == user_id))
                await cleanup.commit()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
