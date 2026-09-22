from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application


class ApplicationRepository:
    """Acceso a la tabla `applications`.

    Nunca hace commit: la transacción la abre y la confirma el service.
    F0: sin `user_id`; desde F2 todos los métodos lo recibirán y filtrarán por él.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, application: Application) -> Application:
        self.session.add(application)
        # flush envía el INSERT dentro de la transacción abierta: Postgres genera
        # id y created_at (server_default) y SQLAlchemy los lee con RETURNING.
        await self.session.flush()
        return application

    async def list(self, *, page: int, limit: int) -> tuple[list[Application], int]:
        query = select(Application)

        total = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )

        result = await self.session.scalars(
            query.order_by(Application.created_at.desc(), Application.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )

        return list(result.all()), total or 0
