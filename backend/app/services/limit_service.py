import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import LimitReachedError
from app.domain.limits import LIMIT_RULES, LimitKey, remaining
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.reminder_repository import ReminderRepository
from app.repositories.user_limit_override_repository import (
    UserLimitOverrideRepository,
)


@dataclass(frozen=True)
class LimitUsage:
    key: LimitKey
    used: int
    # None: sin límite (excepción de la cuenta, solo donde se permite).
    limit: int | None
    remaining: int | None
    renews: bool
    # Si el límite es una excepción de esta cuenta. Solo para administración (el
    # script); la API no lo publica.
    overridden: bool = False


class LimitService:
    """Límites por usuario (RF-140…143, límites y abuso §1).

    El valor de cada límite es la excepción de la cuenta, si la tiene, o el global
    de la configuración. El consumo se **calcula** contando las filas reales, nunca
    se guarda en un contador: un borrado en cascada, un script o un fallo a medias
    lo dejarían desincronizado para siempre.

    Contar e insertar van en la misma transacción pero **sin** bloqueo (como en la
    v1): dos peticiones simultáneas pueden pasarse en uno, y eso no cuesta nada.
    Los límites con coste real (almacenamiento, IA) bloquearán la fila del usuario.
    """

    def __init__(self, session: AsyncSession, config: Settings = settings) -> None:
        self.session = session
        self.config = config
        self.overrides = UserLimitOverrideRepository(session)
        self.applications = ApplicationRepository(session)
        self.companies = CompanyRepository(session)
        self.reminders = ReminderRepository(session)

    def global_limit(self, key: LimitKey) -> int:
        value: int = getattr(self.config, f"limit_{key.value}")
        return value

    async def limit_for(self, user_id: uuid.UUID, key: LimitKey) -> int | None:
        """El de la excepción de la cuenta o el global. None: sin límite."""
        override = await self.overrides.get(user_id, key)
        return override.value if override is not None else self.global_limit(key)

    async def usage_for(self, user_id: uuid.UUID, key: LimitKey) -> int:
        match key:
            case LimitKey.APPLICATIONS:
                return await self.applications.count(user_id)
            case LimitKey.COMPANIES:
                return await self.companies.count(user_id)
            case LimitKey.REMINDERS:
                return await self.reminders.count(user_id)

    async def check(self, user_id: uuid.UUID, key: LimitKey, amount: int = 1) -> None:
        """Lanza LimitReachedError si crear `amount` más superaría el límite."""
        limit = await self.limit_for(user_id, key)
        if limit is None:
            return
        used = await self.usage_for(user_id, key)
        if used + amount > limit:
            raise LimitReachedError(LIMIT_RULES[key].error_code, limit=limit, used=used)

    async def usage(self, user_id: uuid.UUID) -> list[LimitUsage]:
        """Todos los límites de la cuenta, para GET /me/usage (RF-141)."""
        overrides = await self.overrides.get_all(user_id)
        result = []
        for key in LimitKey:
            used = await self.usage_for(user_id, key)
            limit = overrides[key] if key in overrides else self.global_limit(key)
            result.append(
                LimitUsage(
                    key=key,
                    used=used,
                    limit=limit,
                    remaining=remaining(used, limit),
                    renews=LIMIT_RULES[key].renews,
                    overridden=key in overrides,
                )
            )
        return result

    async def set_override(
        self, user_id: uuid.UUID, key: LimitKey, value: int | None
    ) -> None:
        """Excepción de un límite para esta cuenta (RF-143). Rebajarla por debajo de
        lo ya creado no borra nada: solo impide crear más. `None` es "sin límite",
        solo en los límites que lo admiten (la BD también lo impide)."""
        if value is None and not LIMIT_RULES[key].allows_unlimited:
            raise ValueError(f"{key.value} tiene que tener un límite")
        if value is not None and value < 0:
            raise ValueError("El límite no puede ser negativo")
        await self.overrides.upsert(user_id, key, value)
        await self.session.commit()

    async def clear_override(self, user_id: uuid.UUID, key: LimitKey) -> None:
        """Vuelve al valor global de la instalación."""
        await self.overrides.delete(user_id, key)
        await self.session.commit()
