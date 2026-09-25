import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    # Starlette tipa los handlers con Exception; solo se registra para AppException.
    assert isinstance(exc, AppException)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            **exc.extra,
            "detail": exc.message,
            "code": exc.code,
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled exception: %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
        },
    )
