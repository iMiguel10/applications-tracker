import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_interview_service
from app.schemas.common import error_responses
from app.schemas.interview import InterviewCreate, InterviewRead, InterviewUpdate
from app.schemas.user import CurrentUser
from app.services.interview_service import InterviewService

router = APIRouter(
    prefix="/applications/{application_id}/interviews", tags=["Interviews"]
)


@router.get(
    "",
    summary="Listar las entrevistas de una solicitud",
    responses=error_responses(404),
)
async def list_interviews(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewRead]:
    """Entrevistas de la solicitud, ordenadas por fecha (RF-23)."""
    interviews = await service.list(current_user.id, application_id)
    return [InterviewRead.model_validate(interview) for interview in interviews]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Añadir una entrevista",
    responses=error_responses(404, 422),
)
async def create_interview(
    application_id: uuid.UUID,
    data: InterviewCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewRead:
    """Registra una entrevista de la solicitud (RF-40). No cambia el estado: si la
    solicitud está en `applied` o `screening`, el frontend propone pasarla a
    `interviewing` usando `allowed_transitions` (RF-42), sin forzarlo."""
    return InterviewRead.model_validate(
        await service.create(current_user.id, application_id, data)
    )


@router.patch(
    "/{interview_id}",
    summary="Editar una entrevista",
    responses=error_responses(404, 422),
)
async def update_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    data: InterviewUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewRead:
    """Actualización parcial (RF-40): solo cambian los campos enviados. Incluye
    `outcome`, que es como se registra el resultado (RF-41)."""
    return InterviewRead.model_validate(
        await service.update(current_user.id, application_id, interview_id, data)
    )


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una entrevista",
    responses=error_responses(404),
)
async def delete_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> None:
    """Borra la entrevista (RF-40)."""
    await service.delete(current_user.id, application_id, interview_id)
