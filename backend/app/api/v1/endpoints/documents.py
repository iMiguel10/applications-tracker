from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1.deps import (
    enforce_upload_rate_limit,
    get_current_user,
    get_document_service,
    require_verified_email,
)
from app.domain.documents import DocumentKind
from app.schemas.common import ErrorResponse, error_responses
from app.schemas.document import DocumentListQuery, DocumentRead
from app.schemas.pagination import Page
from app.schemas.user import CurrentUser
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", summary="Listar la biblioteca de documentos")
async def list_documents(
    query: Annotated[DocumentListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> Page[DocumentRead]:
    """CVs y cartas del usuario (RF-90), los más recientes primero. Por defecto sin
    los archivados; con `archived=true`, solo ellos."""
    items, total = await service.list(current_user.id, query)
    return Page[DocumentRead].build(
        [DocumentRead.model_validate(item) for item in items],
        total=total,
        page=query.page,
        limit=query.limit,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Subir un PDF",
    responses=error_responses(409, 422)
    | {
        403: {
            "model": ErrorResponse,
            "description": "`email_not_verified`: subir documentos exige el email "
            "verificado (salvo en una instalación sin correo).",
        },
        413: {
            "model": ErrorResponse,
            "description": "`file_too_large`: pasa del tamaño máximo (`max_bytes`).",
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "El PDF, tal cual (no `multipart/form-data`).",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_document(
    request: Request,
    kind: Annotated[DocumentKind, Query(description="`cv` o `cover_letter`.")],
    name: Annotated[
        str | None,
        Query(
            max_length=1000,
            description="Nombre del fichero, para mostrarlo. Se sanea y se recorta "
            "a 200 caracteres; nunca se usa como ruta.",
        ),
    ] = None,
    current_user: CurrentUser = Depends(require_verified_email),
    _rate_limit: None = Depends(enforce_upload_rate_limit),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    """Sube un CV o una carta en PDF a la biblioteca (RF-90). El cuerpo es el PDF
    en crudo: `Content-Type: application/pdf`, con `kind` y `name` en la query.

    Se comprueba el contenido, no la extensión (RF-94): 422 `invalid_file_type` si
    no es un PDF que se pueda abrir, o si está protegido con contraseña. El cuerpo
    se deja de leer al pasar del tamaño máximo de la instalación (413
    `file_too_large`; 5 MB por defecto, `max_document_bytes` en `GET /meta`).

    409 `documents_limit_reached` o `storage_limit_reached` al alcanzar el límite de
    documentos o de almacenamiento de la cuenta (el almacenamiento, en bytes), con
    `limit` y `used`. 30 subidas por hora como máximo (429 `rate_limited`)."""
    document = await service.upload(
        current_user.id, kind=kind, name=name, body=request.stream()
    )
    return DocumentRead.model_validate(document)
