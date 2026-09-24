"""DESECHABLE (F9). Esqueleto vertical de la v2:
endpoint → cola → worker → PDF → disco → email → descarga por la API.

Existe para descubrir dónde están las dificultades de la infraestructura nueva
antes de construir encima (especificación §11). Se borra al terminar F9 junto con
su endpoint, su trabajo, su plantilla y sus pruebas; lo que queda son las piezas
de `infra/`.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.infra.email import EmailSender, OutgoingEmail
from app.infra.pdf import PdfRenderer
from app.infra.queue import JobQueue
from app.infra.storage import FileStorage, StorageKeyNotFoundError
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

SPIKE_PDF_JOB = "generate_spike_pdf"
SPIKE_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "spike"


def spike_pdf_key(user_id: uuid.UUID, file_id: uuid.UUID) -> str:
    # La ruta la genera el servidor y lleva el user_id (A23): un file_id de otro
    # usuario, pedido con mi user_id, apunta a un fichero que no existe → 404.
    return f"users/{user_id}/spike/{file_id}.pdf"


class SpikeService:
    """Lado de la API: encola y vuelve enseguida (RNF-12), y sirve la descarga."""

    def __init__(self, queue: JobQueue, storage: FileStorage) -> None:
        self.queue = queue
        self.storage = storage

    async def request_pdf(self, current_user: CurrentUser) -> uuid.UUID:
        file_id = uuid.uuid4()
        # Sin fila que confirmar, no hay commit previo; en un caso real se
        # encolaría después de confirmar la fila `pending` (invariante 11).
        await self.queue.enqueue(
            SPIKE_PDF_JOB,
            timeout_seconds=60,
            # Un solo intento: el trabajo acaba enviando un email, y un reintento
            # tras el envío lo duplicaría (segundo plano §2).
            max_attempts=1,
            key=str(file_id),
            user_id=str(current_user.id),
            file_id=str(file_id),
        )
        return file_id

    async def open_pdf(
        self, current_user: CurrentUser, file_id: uuid.UUID
    ) -> AsyncIterator[bytes]:
        try:
            return await self.storage.open(spike_pdf_key(current_user.id, file_id))
        except StorageKeyNotFoundError as exc:
            raise NotFoundError("PDF") from exc


class SpikePdfService:
    """Lado del worker: genera el PDF, lo guarda y avisa por email con el enlace."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        pdf_renderer: PdfRenderer,
        storage: FileStorage,
        email_sender: EmailSender,
        identities: IdentityRepository,
        api_url: str,
    ) -> None:
        self.users = UserRepository(session)
        self.pdf_renderer = pdf_renderer
        self.storage = storage
        self.email_sender = email_sender
        self.identities = identities
        self.api_url = api_url.rstrip("/")

    async def generate_and_send(self, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
        user = await self.users.get_by_id(user_id)
        if user is None:
            return  # borró su cuenta entre el encolado y el trabajo
        address = await self.identities.get_email(user.supertokens_user_id)
        if address is None:
            return

        pdf = await self.pdf_renderer.render(
            SPIKE_TEMPLATE_DIR,
            {"address": address, "generated_at": datetime.now(UTC)},
        )
        await self.storage.put(spike_pdf_key(user_id, file_id), _single_chunk(pdf))

        link = f"{self.api_url}/api/v1/spike/pdf/{file_id}"
        await self.email_sender.send(
            OutgoingEmail(
                to=address,
                subject="Tu PDF de prueba está listo",
                text=f"El worker ha generado tu PDF de prueba. Descárgalo aquí "
                f"(con la sesión iniciada en este navegador):\n\n{link}\n",
                html=f'<p>El worker ha generado tu PDF de prueba.</p><p><a href="{link}">'
                "Descargar el PDF</a> (con la sesión iniciada en este navegador).</p>",
            )
        )


async def _single_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content
