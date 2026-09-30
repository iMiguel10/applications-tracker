"""El bucle común de los barridos de avisos (segundo plano §3): leer candidatos por
páginas, preguntar a SuperTokens si el email está verificado (una vez por cuenta y
pasada), reclamar cada aviso y encolar su envío."""

import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import SWEEP_MAX_CLAIMS, NotificationKind
from app.infra.queue import JobQueue
from app.repositories.identity_repository import IdentityRepository
from app.services.notification_delivery_service import NotificationDeliveryService

logger = logging.getLogger(__name__)

# Candidatos que se leen por consulta. Se sigue leyendo hasta agotarlos o hasta
# SWEEP_MAX_CLAIMS reclamos: si se leyera una sola página, las cuentas sin verificar
# (que no reclaman) podrían ocuparla entera y dejar sin aviso a las demás.
PAGE_SIZE = 200

Cursor = tuple[datetime, uuid.UUID]


@dataclass(frozen=True)
class SweepCandidate:
    user_id: uuid.UUID
    supertokens_user_id: str
    dedupe_key: str
    # Posición en el orden de la consulta, para pedir la página siguiente.
    cursor: Cursor


FetchPage = Callable[[Cursor | None, int], Awaitable[Sequence[SweepCandidate]]]


class ClaimingSweep:
    """Reclama los avisos de un tipo que devuelve `fetch_page`. La consulta ya
    filtra por el aviso activado y por las entregas que lo impiden; aquí se añade el
    email verificado: una cuenta sin verificar no genera ni reclamos, así que al
    verificarla no recibe de golpe lo acumulado."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.deliveries = NotificationDeliveryService(session)
        self.job_queue = job_queue
        self.identities = identities or IdentityRepository()

    async def claim_all(
        self, kind: NotificationKind, fetch_page: FetchPage, now: datetime
    ) -> int:
        verified: dict[str, bool] = {}
        claimed = 0
        after: Cursor | None = None
        while claimed < SWEEP_MAX_CLAIMS:
            candidates = await fetch_page(after, PAGE_SIZE)
            if not candidates:
                break
            for candidate in candidates:
                account = candidate.supertokens_user_id
                if account not in verified:
                    verified[account] = await self.identities.is_email_verified(account)
                if not verified[account]:
                    continue
                delivery_id = await self.deliveries.claim(
                    candidate.user_id, kind, candidate.dedupe_key, now
                )
                if delivery_id is None:
                    continue
                await self.deliveries.enqueue_send(
                    self.job_queue, delivery_id, candidate.user_id
                )
                claimed += 1
                if claimed >= SWEEP_MAX_CLAIMS:
                    break
            after = candidates[-1].cursor
        if claimed:
            logger.info("%d avisos %s reclamados", claimed, kind.value)
        return claimed
