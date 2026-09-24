"""`WeasyPrintRenderer`: genera PDF de verdad (en la imagen, con sus librerías de
sistema) y no descarga nada fuera de la carpeta de la plantilla (ficheros §7, D9)."""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self

import pytest
from jinja2 import UndefinedError
from weasyprint.urls import URLFetchingError  # type: ignore[import-untyped]

from app.infra.pdf.weasyprint_renderer import TemplateOnlyFetcher, WeasyPrintRenderer


class CountingServer:
    """Servidor HTTP local que cuenta cada petición que recibe."""

    def __init__(self) -> None:
        self.requests: list[str] = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def __enter__(self) -> Self:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args: object) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def counting_server() -> Iterator[CountingServer]:
    with CountingServer() as server:
        yield server


def write_template(directory: Path, html: str, css: str = "") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "template.html").write_text(html, encoding="utf-8")
    (directory / "style.css").write_text(css, encoding="utf-8")
    return directory


@pytest.mark.asyncio
async def test_renders_a_pdf_with_the_context(tmp_path: Path) -> None:
    template = write_template(
        tmp_path / "design",
        '<link rel="stylesheet" href="style.css"><p>Hola, {{ name }}: currículum</p>',
        "body { font-family: sans-serif; }",
    )

    pdf = await WeasyPrintRenderer().render(template, {"name": "Ana"})

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


@pytest.mark.asyncio
async def test_context_is_autoescaped(tmp_path: Path) -> None:
    """Todo el contenido lo escribe el usuario o la IA: nunca se interpreta como HTML.
    Un `<img>` inyectado en un dato no llega a pedirse."""
    template = write_template(tmp_path / "design", "<p>{{ name }}</p>")

    with CountingServer() as server:
        await WeasyPrintRenderer().render(
            template, {"name": f'<img src="{server.url}/inyectado.png">'}
        )

    assert server.requests == []


@pytest.mark.asyncio
async def test_undefined_variable_fails_instead_of_rendering_empty(
    tmp_path: Path,
) -> None:
    template = write_template(tmp_path / "design", "<p>{{ nmae }}</p>")

    with pytest.raises(UndefinedError):
        await WeasyPrintRenderer().render(template, {"name": "Ana"})


@pytest.mark.asyncio
async def test_no_network_request_from_the_template(
    tmp_path: Path, counting_server: CountingServer
) -> None:
    """D9: imágenes, hojas de estilo y fuentes externas en la propia plantilla no
    producen ninguna petición, y el PDF se genera igual, sin esos recursos."""
    url = counting_server.url
    template = write_template(
        tmp_path / "design",
        '<link rel="stylesheet" href="style.css">'
        f'<link rel="stylesheet" href="{url}/externo.css">'
        f'<img src="{url}/logo.png"><p style="font-family: X">Texto</p>',
        f'@font-face {{ font-family: X; src: url("{url}/fuente.woff2"); }}'
        f'body {{ background: url("{url}/fondo.png"); }}',
    )

    pdf = await WeasyPrintRenderer().render(template, {})

    assert pdf.startswith(b"%PDF-")
    assert counting_server.requests == []


# Cada uno de estos HTML produce una petición con el fetcher por defecto de
# WeasyPrint 70 (comprobado a mano al escribir la prueba): no son vectores
# teóricos. `{url}` es el servidor que cuenta las peticiones.
MORE_NETWORK_VECTORS = {
    "css_import": '<style>@import url("{url}/import.css");</style><p>x</p>',
    "attachment": '<link rel="attachment" href="{url}/adjunto.bin"><p>x</p>',
    "anchor_attachment": '<a rel="attachment" href="{url}/adjunto.bin">a</a>',
    "object": '<object data="{url}/objeto.png" type="image/png"></object>',
    "embed": '<embed src="{url}/embed.png" type="image/png">',
    "svg_image": (
        '<svg width="10" height="10">'
        '<image href="{url}/svg.png" width="10" height="10"/></svg>'
    ),
    "base_href": '<base href="{url}/"><img src="relativa.png">',
    "list_style_image": (
        '<ul style="list-style-image: url({url}/vineta.png)"><li>x</li></ul>'
    ),
    "content_url": (
        '<style>p::before {{ content: url("{url}/antes.png"); }}</style><p>x</p>'
    ),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("vector", MORE_NETWORK_VECTORS)
async def test_no_network_request_from_other_resource_kinds(
    tmp_path: Path, counting_server: CountingServer, vector: str
) -> None:
    """D9 más allá de imágenes, hojas de estilo, fuentes y fondos: todo recurso
    que WeasyPrint sabe descargar pasa por el mismo fetcher."""
    html = MORE_NETWORK_VECTORS[vector].format(url=counting_server.url)
    template = write_template(tmp_path / "design", html)

    pdf = await WeasyPrintRenderer().render(template, {})

    assert pdf.startswith(b"%PDF-")
    assert counting_server.requests == []


@pytest.mark.asyncio
async def test_local_file_outside_the_template_is_not_embedded(
    tmp_path: Path,
) -> None:
    """`<link rel="attachment">` incrusta el fichero enlazado dentro del PDF: con
    una ruta `file://` fuera de la plantilla sería leer ficheros del worker y
    entregarlos al usuario. Con el fetcher por defecto sí se incrusta."""
    secret = tmp_path / "secreto.txt"
    secret.write_text("no debe salir", encoding="utf-8")
    template = write_template(
        tmp_path / "design",
        f'<link rel="attachment" href="{secret.as_uri()}"><p>x</p>',
    )

    pdf = await WeasyPrintRenderer().render(template, {})

    assert b"/EmbeddedFile" not in pdf


def test_fetcher_serves_only_files_inside_the_template(tmp_path: Path) -> None:
    template = write_template(tmp_path / "design", "<p></p>", "p {}")
    (tmp_path / "secreto.txt").write_text("fuera", encoding="utf-8")
    fetcher = TemplateOnlyFetcher(template)

    inside = fetcher.fetch((template / "style.css").as_uri())
    assert inside.read() == b"p {}"

    for url in [
        (tmp_path / "secreto.txt").as_uri(),
        (template / ".." / "secreto.txt").as_uri(),
        "file:///etc/passwd",
        "http://supertokens:3567/hello",
        "https://example.com/logo.png",
        "ftp://example.com/x",
    ]:
        with pytest.raises((URLFetchingError, ValueError)):
            fetcher.fetch(url)
