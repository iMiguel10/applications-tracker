import asyncio
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from weasyprint import HTML  # type: ignore[import-untyped]
from weasyprint.urls import URLFetcher, URLFetchingError  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

TEMPLATE_FILE = "template.html"


class TemplateOnlyFetcher(URLFetcher):
    """Solo deja a WeasyPrint leer ficheros de la carpeta del diseño (y `data:`).

    Al renderizar, WeasyPrint descarga lo que el HTML le pida: imágenes, hojas de
    estilo, fuentes. Si una URL escrita por el usuario acabara en un `<img>` o en
    un `url()`, el worker haría peticiones a donde quisiera, incluidos servicios
    internos de la red de Docker (SSRF, ficheros §7). Todo lo demás se rechaza sin
    abrir ninguna conexión, y WeasyPrint sigue renderizando sin ese recurso.
    """

    def __init__(self, template_dir: Path) -> None:
        super().__init__(allowed_protocols={"file", "data"}, allow_redirects=False)
        self._template_dir = template_dir.resolve()

    def fetch(self, url: str, headers: Mapping[str, str] | None = None) -> Any:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            path = Path(url2pathname(unquote(parsed.path))).resolve()
            if not path.is_relative_to(self._template_dir):
                logger.warning("Recurso fuera de la plantilla rechazado: %s", url)
                raise URLFetchingError(f"fuera de la plantilla: {url}")
        elif parsed.scheme != "data":
            logger.warning("Recurso externo rechazado: %s", url)
            raise URLFetchingError(f"protocolo no permitido: {url}")
        return super().fetch(url, headers)


class WeasyPrintRenderer:
    """`PdfRenderer` con Jinja2 + WeasyPrint (A24)."""

    async def render(self, template_dir: Path, context: Mapping[str, Any]) -> bytes:
        # Maquetar es cálculo puro (1-3 s): en un hilo, para que el worker siga
        # atendiendo los demás trabajos mientras tanto.
        return await asyncio.to_thread(self._render, template_dir, context)

    def _render(self, template_dir: Path, context: Mapping[str, Any]) -> bytes:
        environment = Environment(
            loader=FileSystemLoader(template_dir),
            # Todo el contenido lo escribe el usuario o la IA.
            autoescape=True,
            # Una variable mal escrita en la plantilla falla, en vez de salir vacía.
            undefined=StrictUndefined,
        )
        html = environment.get_template(TEMPLATE_FILE).render(context)
        document = HTML(
            string=html,
            # Barra final: las rutas relativas (style.css, fonts/…) se resuelven
            # DENTRO de la carpeta del diseño.
            base_url=template_dir.resolve().as_uri() + "/",
            url_fetcher=TemplateOnlyFetcher(template_dir),
        )
        pdf: bytes = document.write_pdf()
        return pdf
