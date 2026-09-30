import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import (
    enforce_upload_rate_limit,
    get_current_user,
    get_document_service,
    require_verified_email,
)
from app.domain.documents import DocumentKind, content_disposition
from app.schemas.common import ErrorResponse, error_responses
from app.schemas.document import (
    DocumentDetailRead,
    DocumentListItemRead,
    DocumentListQuery,
    DocumentRead,
    DocumentUpdate,
    DocumentUsageRead,
)
from app.schemas.pagination import Page
from app.schemas.user import CurrentUser
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", summary="Listar la biblioteca de documentos")
async def list_documents(
    query: Annotated[DocumentListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> Page[DocumentListItemRead]:
    """CVs y cartas del usuario (RF-90), los más recientes primero, cada uno con en
    cuántas solicitudes se envió (RF-92). Por defecto sin los archivados; con
    `archived=true`, solo ellos."""
    items, total = await service.list(current_user.id, query)
    return Page[DocumentListItemRead].build(
        [
            DocumentListItemRead(
                **DocumentRead.model_validate(document).model_dump(),
                applications_count=count,
            )
            for document, count in items
        ],
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


@router.get(
    "/{document_id}/file",
    summary="Descargar o ver el PDF",
    response_class=StreamingResponse,
    responses=error_responses(404, 409)
    | {
        200: {
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
            "description": "El PDF.",
        }
    },
)
async def get_document_file(
    document_id: uuid.UUID,
    download: Annotated[
        bool,
        Query(
            description="`true`: `Content-Disposition: attachment` (descargar). "
            "`false` (por defecto): `inline`, para verlo en el navegador."
        ),
    ] = False,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> StreamingResponse:
    """El PDF de un documento del usuario (RF-90), siempre como `application/pdf`
    con `X-Content-Type-Options: nosniff`, nunca con el tipo que dijo el cliente al
    subirlo (RNF-05). `Content-Disposition` lleva el nombre en ASCII (`filename`) y
    en UTF-8 (`filename*`). `Cache-Control: private, no-store`: un CV no debe
    quedarse en la caché de un proxy.

    404 si no existe o es de otro usuario; 409 `document_not_ready` si todavía no
    tiene fichero (un documento generado que no ha terminado)."""
    document, chunks = await service.open_file(current_user.id, document_id)
    headers = {
        "Content-Disposition": content_disposition(document.name, attachment=download),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    if document.size_bytes is not None:
        headers["Content-Length"] = str(document.size_bytes)
    return StreamingResponse(chunks, media_type="application/pdf", headers=headers)


@router.get(
    "/{document_id}", summary="Ver un documento", responses=error_responses(404)
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentDetailRead:
    """Los datos de un documento (RF-91: de dónde sale) y las solicitudes en que se
    envió (RF-92). El PDF, en `GET /documents/{document_id}/file`."""
    document = await service.get(current_user.id, document_id)
    usage = await service.usage(current_user.id, document_id)
    return DocumentDetailRead(
        **DocumentRead.model_validate(document).model_dump(),
        used_in=[DocumentUsageRead.model_validate(item) for item in usage],
    )


@router.patch(
    "/{document_id}",
    summary="Renombrar un documento",
    responses=error_responses(404, 422),
)
async def rename_document(
    document_id: uuid.UUID,
    data: DocumentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    """Cambia el nombre visible (RF-90). Se sanea como al subir; el fichero en
    disco no cambia."""
    return DocumentRead.model_validate(
        await service.rename(current_user.id, document_id, data.name)
    )


@router.post(
    "/{document_id}/archive",
    summary="Archivar un documento",
    responses=error_responses(404),
)
async def archive_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    """Lo saca de la biblioteca sin borrarlo (RF-93): sigue asociado a las
    solicitudes en que se usó y sigue ocupando almacenamiento. Idempotente."""
    return DocumentRead.model_validate(
        await service.archive(current_user.id, document_id)
    )


@router.post(
    "/{document_id}/unarchive",
    summary="Desarchivar un documento",
    responses=error_responses(404),
)
async def unarchive_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    """Lo devuelve a la biblioteca. Idempotente."""
    return DocumentRead.model_validate(
        await service.unarchive(current_user.id, document_id)
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un documento",
    responses=error_responses(404, 409),
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> None:
    """Borra el documento y su PDF, y libera su espacio. Definitivo.

    409 `document_in_use` si se envió en alguna solicitud (RF-93), con
    `applications` (en cuántas): borrarlo perdería qué se envió a quién. Se puede
    archivar."""
    await service.delete(current_user.id, document_id)
