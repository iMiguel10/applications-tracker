from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.repositories.application_repository import ApplicationRepository
from app.schemas.application import ApplicationCreate


class ApplicationService:
    """Reglas de negocio de las solicitudes. Dueño de la transacción: es quien hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.applications = ApplicationRepository(session)

    async def create(self, data: ApplicationCreate) -> Application:
        application = await self.applications.add(
            Application(
                position_title=data.position_title,
                company_name=data.company_name,
            )
        )
        await self.session.commit()
        return application

    async def list(self, *, page: int, limit: int) -> tuple[list[Application], int]:
        return await self.applications.list(page=page, limit=limit)
