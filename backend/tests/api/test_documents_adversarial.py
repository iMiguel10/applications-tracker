"""Pruebas adversas de la subida y la descarga de documentos (ficheros §2, §4 y
§8: D1, D2, D8). Añadidas por el qa-verifier al cerrar F13."""

import io
import re
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_file_storage
from app.domain.documents import DEFAULT_NAME, content_disposition
from app.domain.limits import LimitKey
from app.infra.storage import LocalFileStorage
from app.main import app
from app.models.document import Document
from app.schemas.user import CurrentUser
from app.services.limit_service import LimitService
from tests.pdf_helpers import make_pdf

URL = "/api/v1/documents"
PDF = {"Content-Type": "application/pdf"}

# Un Content-Disposition bien formado: el nombre ASCII entre comillas sin
# comillas, barras invertidas ni caracteres de control dentro, y el UTF-8 solo
# con caracteres no reservados o escapados con %.
SAFE_DISPOSITION = re.compile(
    r"^(inline|attachment); filename=\"[^\"\\\x00-\x1f\x7f]+\"; "
    r"filename\*=UTF-8''[A-Za-z0-9%._~-]+$"
)


@pytest.fixture(autouse=True)
def _storage(tmp_path: Path) -> Iterator[None]:
    app.dependency_overrides[get_file_storage] = lambda: LocalFileStorage(tmp_path)
    yield
    app.dependency_overrides.pop(get_file_storage, None)


def _stored_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and ".tmp" not in p.parts]


async def _upload(client: AsyncClient, content: bytes, name: str) -> httpx.Response:
    return await client.post(
        URL, params={"kind": "cv", "name": name}, content=content, headers=PDF
    )


# --- D8: nombres maliciosos en Content-Disposition -----------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("cv.pdf\r\nSet-Cookie: sAccessToken=robado", id="crlf"),
        pytest.param('a";filename="evil.exe', id="comillas-y-otro-filename"),
        pytest.param("cv\\\\..\\\\x.pdf", id="barras-invertidas"),
        pytest.param("cv" + chr(0x202E) + "fdp.exe", id="override-direccion"),
        pytest.param("a; b=c; filename*=UTF-8''evil.exe", id="parametros-extra"),
        pytest.param("x" * 1000, id="larguisimo"),
    ],
)
async def test_a_malicious_name_never_breaks_the_download_headers(
    client: AsyncClient, name: str
):
    uploaded = await _upload(client, make_pdf(), name)
    assert uploaded.status_code == 201
    stored_name = uploaded.json()["name"]

    response = await client.get(f"{URL}/{uploaded.json()['id']}/file")

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert SAFE_DISPOSITION.match(disposition), disposition
    # Ninguna cabecera inyectada.
    assert "set-cookie" not in response.headers
    # El nombre UTF-8 dice exactamente el nombre visible (más .pdf si no lo lleva).
    # El último parámetro: el nombre ASCII entrecomillado puede contener el texto
    # "filename*=" (ese es precisamente uno de los casos).
    utf8 = unquote(disposition.rsplit("; filename*=UTF-8''", 1)[1])
    expected = (
        stored_name if stored_name.lower().endswith(".pdf") else f"{stored_name}.pdf"
    )
    assert utf8 == expected


# Si ningún carácter del nombre sobrevive a ASCII, `filename` quedaba en ".pdf" (un
# fichero oculto sin nombre) en vez de caer en DEFAULT_NAME (encontrado por el
# qa-verifier en F13).
@pytest.mark.parametrize("name", ["履歴書.pdf", "Резюме", "简历.PDF"])
def test_a_name_without_ascii_letters_falls_back_to_a_default_ascii_name(
    name: str,
) -> None:
    disposition = content_disposition(name, attachment=True)

    ascii_name = disposition.split('filename="', 1)[1].split('"', 1)[0]
    assert ascii_name == DEFAULT_NAME, disposition


# --- D2: Content-Length que miente ---------------------------------------------


async def _body(content: bytes) -> AsyncGenerator[bytes, None]:
    # Dos trozos: el cuerpo llega en más de un paso.
    middle = len(content) // 2
    yield content[:middle]
    yield content[middle:]


@pytest.mark.asyncio
async def test_the_stored_size_is_the_real_one_not_the_declared_one(
    client: AsyncClient, db_session: AsyncSession
):
    content = make_pdf(pages=3)

    response = await client.post(
        URL,
        params={"kind": "cv", "name": "cv.pdf"},
        content=_body(content),
        headers=PDF | {"Content-Length": "10"},
    )

    assert response.status_code == 201
    assert response.json()["size_bytes"] == len(content)


@pytest.mark.asyncio
async def test_a_small_declared_size_does_not_sneak_past_the_storage_limit(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, tmp_path: Path
):
    content = make_pdf()
    await LimitService(db_session).set_override(
        user.id, LimitKey.STORAGE_BYTES, len(content) - 1
    )

    response = await client.post(
        URL,
        params={"kind": "cv", "name": "cv.pdf"},
        content=_body(content),
        headers=PDF | {"Content-Length": "10"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "storage_limit_reached"
    assert response.json()["used"] == 0
    assert _stored_files(tmp_path) == []


# --- D1: más PDFs que no lo son ------------------------------------------------


def _pdf_without_pages() -> bytes:
    buffer = io.BytesIO()
    PdfWriter().write(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        pytest.param(_pdf_without_pages(), id="sin-paginas"),
        pytest.param(b" " + make_pdf(), id="firma-desplazada"),
        pytest.param(b"%PDF-1.7\n" + b"\x00" * 4096 + b"\n%%EOF", id="binario-basura"),
        pytest.param(b"<html><script>alert(1)</script></html>%PDF-", id="html"),
    ],
)
async def test_more_things_that_are_not_a_usable_pdf_are_rejected(
    client: AsyncClient, db_session: AsyncSession, tmp_path: Path, content: bytes
):
    response = await _upload(client, content, "cv.pdf")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file_type"
    assert _stored_files(tmp_path) == []
    assert await db_session.scalar(select(Document.id)) is None
