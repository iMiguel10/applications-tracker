"""DESECHABLE (F9): endpoints del esqueleto vertical. Ver services/spike_service.py."""

import unicodedata
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, get_spike_service
from app.schemas.user import CurrentUser
from app.services.spike_service import SpikeService

router = APIRouter(
    prefix="/spike",
    tags=["Spike"],
)

# Con tilde a propósito: comprueba la cabecera con filename* (ficheros §4, D8).
DOWNLOAD_NAME = "prueba-currículum.pdf"


class SpikePdfRequested(BaseModel):
    file_id: uuid.UUID


@router.post(
    "/pdf",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encola la generación de un PDF de prueba (F9, desechable)",
)
async def request_spike_pdf(
    current_user: CurrentUser = Depends(get_current_user),
    spike: SpikeService = Depends(get_spike_service),
) -> SpikePdfRequested:
    """Encola un trabajo que el worker ejecuta aparte: genera un PDF, lo guarda en
    el almacén de ficheros y envía un email al usuario con el enlace de descarga.
    Responde 202 sin esperar. Temporal: se retira al cerrar F9."""
    return SpikePdfRequested(file_id=await spike.request_pdf(current_user))


@router.get(
    "/pdf/{file_id}",
    summary="Descarga el PDF de prueba (F9, desechable)",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_spike_pdf(
    file_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    spike: SpikeService = Depends(get_spike_service),
) -> StreamingResponse:
    """Devuelve el PDF generado por `POST /spike/pdf`. 404 si todavía no existe o
    si es de otro usuario. Temporal: se retira al cerrar F9."""
    content = await spike.open_pdf(current_user, file_id)
    return StreamingResponse(
        content,
        # Siempre application/pdf, nunca un tipo que dijera el cliente (RNF-05).
        media_type="application/pdf",
        headers={
            "Content-Disposition": _inline_disposition(DOWNLOAD_NAME),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


def _inline_disposition(filename: str) -> str:
    # Una cabecera HTTP solo admite ASCII: `filename` lleva una versión ASCII y
    # `filename*` (RFC 5987) la original en UTF-8, que prefieren los navegadores.
    # NFKD separa "í" en "i" + tilde, y así solo se pierde la tilde, no la letra.
    decomposed = unicodedata.normalize("NFKD", filename)
    ascii_name = decomposed.encode("ascii", "ignore").decode() or "documento.pdf"
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
