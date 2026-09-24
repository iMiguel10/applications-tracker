"""Configuración del worker de SAQ (A18). Solo cablea: registra las funciones de
`jobs/` y crea al arrancar las dependencias que comparten.

    saq app.worker.settings

Usa la misma imagen, código y .env que `api`, pero no su entrypoint: las
migraciones las aplica solo `api` (servicios y estructura §8.1).
"""

from saq import Queue

from app.core.config import settings as config
from app.core.logging import setup_logging
from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.infra.email import build_email_sender
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.infra.storage import LocalFileStorage
from app.jobs.context import WorkerContext
from app.jobs.spike import generate_spike_pdf

# Al importar, como en main.py: SAQ registra el arranque del worker antes de
# llamar a startup(), y sin logging configurado esas líneas no salen.
setup_logging()


async def startup(ctx: WorkerContext) -> None:
    # Los trabajos piden a SuperTokens el email del destinatario (A12): el SDK
    # necesita estar inicializado también en este proceso, no solo en la API.
    init_supertokens()
    ctx["session_factory"] = async_session_factory
    ctx["email_sender"] = build_email_sender(config)
    ctx["storage"] = LocalFileStorage(config.files_root)
    ctx["pdf_renderer"] = WeasyPrintRenderer()
    ctx["api_url"] = config.api_domain


settings = {
    "queue": Queue.from_url(config.valkey_url),
    "functions": [generate_spike_pdf],
    "startup": startup,
    "concurrency": 10,
}
