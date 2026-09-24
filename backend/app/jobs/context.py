from saq.types import Context
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.email import EmailSender
from app.infra.pdf import PdfRenderer
from app.infra.storage import FileStorage


class WorkerContext(Context, total=False):
    """Contexto de SAQ más las dependencias que `worker.py` crea al arrancar y
    comparten todos los trabajos. Declararlas aquí es lo que deja a mypy
    comprobar `ctx["email_sender"]` en vez de tratar el contexto como un dict."""

    session_factory: async_sessionmaker[AsyncSession]
    email_sender: EmailSender
    storage: FileStorage
    pdf_renderer: PdfRenderer
