from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from saq import Queue
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from app.api import auth_docs
from app.api.openapi import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    OPENAPI_TAGS,
    SWAGGER_UI_PARAMETERS,
)
from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.supertokens import init_supertokens
from app.infra.queue import JobQueue, SaqJobQueue


def _job_queue() -> JobQueue:
    # La cola existe desde el lifespan; SuperTokens la pide al encolar un email.
    queue: JobQueue = app.state.job_queue
    return queue


setup_logging()
init_supertokens(job_queue=_job_queue)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # La cola se crea aquí, dentro del event loop del servidor, y no al importar:
    # SAQ guarda primitivas de asyncio que quedan ligadas al primer loop que las usa.
    queue = Queue.from_url(settings.valkey_url)
    await queue.connect()
    app.state.job_queue = SaqJobQueue(queue)
    try:
        yield
    finally:
        await queue.disconnect()


app = FastAPI(
    lifespan=lifespan,
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
)

# Solo documentación: el middleware de SuperTokens atiende /auth/* antes que el router.
app.include_router(auth_docs.router)
app.include_router(api_router, prefix="/api/v1")

# El orden importa: en Starlette el ÚLTIMO add_middleware es el más externo.
# SuperTokens se añade primero y CORS después, para que CORS envuelva también las
# respuestas de /auth/*. Invertido, el login respondería 200 sin
# Access-Control-Allow-Origin y el navegador lo bloquearía (autenticacion.md §3).
app.add_middleware(get_middleware())
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", *get_all_cors_headers()],
)

app.add_exception_handler(
    AppException,
    app_exception_handler,
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)
