"""Comprobar que unos bytes son un PDF de verdad (ficheros §2, paso 3).

El servidor nunca renderiza ni extrae texto de un PDF subido: solo lo abre para
contar sus páginas. Si pypdf no puede, no es un PDF que se vaya a aceptar.
"""

import asyncio
import io
import logging

from pypdf import PdfReader

from app.domain.documents import PDF_SIGNATURE


class InvalidPdfError(Exception):
    """No es un PDF, o no se pudo abrir a tiempo."""


def _count_pages(data: bytes) -> int:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        # Protegido con contraseña: el navegador del dueño no podría mostrarlo sin
        # ella, y la IA de F15 tampoco podría leerlo.
        raise InvalidPdfError("PDF cifrado")
    pages = len(reader.pages)
    if pages < 1:
        raise InvalidPdfError("PDF sin páginas")
    return pages


async def count_pages(data: bytes, *, timeout: float) -> int:
    """Páginas del PDF, o InvalidPdfError. Corre en un hilo para no parar el
    event loop, con un tope de tiempo.

    Un hilo no se puede matar: si pypdf se colgara de verdad, el hilo seguiría
    ocupado aunque la petición ya hubiera respondido. pypdf corta los bucles de
    referencias que conoce, y el rate limit de la subida acota cuántos podrían
    acumularse. Un proceso aparte lo resolvería del todo a cambio de arrancar uno
    por subida; queda anotado en ficheros §9."""
    if not data.startswith(PDF_SIGNATURE):
        raise InvalidPdfError("sin la firma %PDF-")
    try:
        return await asyncio.wait_for(asyncio.to_thread(_count_pages, data), timeout)
    except InvalidPdfError:
        raise
    except TimeoutError as exc:
        raise InvalidPdfError("no se pudo abrir a tiempo") from exc
    except Exception as exc:  # pypdf lanza muchos tipos distintos ante un PDF roto
        raise InvalidPdfError(str(exc)) from exc


# pypdf avisa por el log de cada anomalía que tolera: un PDF raro subido por un
# usuario no es algo que el operador tenga que leer.
logging.getLogger("pypdf").setLevel(logging.ERROR)
