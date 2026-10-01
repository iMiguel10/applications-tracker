"""Maquetar un CV con cada diseño (F14, RF-104, RF-105, RF-106; ficheros §7 y §8:
D10)."""

import io
import re
from typing import cast

import pytest
from pypdf import PdfReader
from pypdf.generic import DictionaryObject

from app.core.exceptions import AppException
from app.domain.cv import CvSnapshot, SnapshotContact
from app.infra.pdf.designs import CvDesignCatalog
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.scripts.render_cv_samples import sample_snapshot
from app.services.cv_render_service import CvRenderService

CATALOG = CvDesignCatalog()
DESIGNS = sorted(CATALOG.designs())
ATS_DESIGNS = [key for key in DESIGNS if CATALOG.designs()[key].ats_friendly]


def _text(pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf))
    # Espacios normalizados: el diseño gráfico parte el nombre en varias líneas.
    return " ".join(" ".join(page.extract_text() for page in reader.pages).split())


def _fonts(pdf: bytes) -> set[str]:
    names: set[str] = set()
    for page in PdfReader(io.BytesIO(pdf)).pages:
        resources = cast(DictionaryObject, page["/Resources"].get_object())
        fonts = cast(DictionaryObject, resources.get("/Font", DictionaryObject()))
        for font in fonts.values():
            names.add(str(cast(DictionaryObject, font.get_object())["/BaseFont"]))
    return names


def test_there_are_four_designs_and_one_is_not_ats_friendly():
    # Decisión del usuario al empezar F14: tres aptos para ATS y uno gráfico.
    assert DESIGNS == ["classic", "compact", "graphic", "modern"]
    assert ATS_DESIGNS == ["classic", "compact", "modern"]


@pytest.mark.parametrize("key", DESIGNS)
def test_every_design_has_names_in_both_languages_and_its_fonts(key: str):
    design = CATALOG.designs()[key]
    assert set(design.names) == {"es", "en"}
    assert set(design.descriptions) == {"es", "en"}
    assert set(design.languages) == {"es", "en"}
    # Cada fuente del CSS existe en la carpeta del diseño: si faltara, WeasyPrint
    # usaría DejaVu sin avisar.
    folder = CATALOG.design_dir(key)
    css = (folder / "style.css").read_text(encoding="utf-8")
    for font in re.findall(r'url\("(fonts/[^"]+)"\)', css):
        assert (folder / font).is_file(), font


@pytest.mark.asyncio
@pytest.mark.parametrize("key", DESIGNS)
@pytest.mark.parametrize("language", ["es", "en"])
async def test_every_design_renders_the_sample_profile(key: str, language: str):
    pdf = await CvRenderService(WeasyPrintRenderer()).render(
        sample_snapshot(), key, language
    )

    text = _text(pdf)
    assert pdf.startswith(b"%PDF-")
    assert "Lucía Fernández Ortega" in text
    assert ("Experiencia" if language == "es" else "Experience") in text
    assert ("actualidad" if language == "es" else "present") in text


@pytest.mark.asyncio
@pytest.mark.parametrize("key", DESIGNS)
async def test_every_design_renders_an_empty_profile(key: str):
    # Con StrictUndefined, una plantilla que use algo que no siempre existe falla
    # aquí y no con el primer usuario que tenga el perfil a medias.
    snapshot = CvSnapshot(contact=SnapshotContact())

    pdf = await CvRenderService(WeasyPrintRenderer()).render(snapshot, key, "es")

    assert pdf.startswith(b"%PDF-")


@pytest.mark.asyncio
@pytest.mark.parametrize("key", DESIGNS)
async def test_every_design_embeds_its_own_fonts(key: str):
    pdf = await CvRenderService(WeasyPrintRenderer()).render(
        sample_snapshot(), key, "es"
    )

    fonts = " ".join(_fonts(pdf))
    assert "DejaVu" not in fonts, fonts


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ATS_DESIGNS)
async def test_d10_ats_designs_extract_in_reading_order(key: str):
    # D10 (RF-105): lo que lee un ATS sale en el orden en que se lee el CV. Un
    # elemento con `position` se pinta en otra capa y su texto saldría al final.
    pdf = await CvRenderService(WeasyPrintRenderer()).render(
        sample_snapshot(), key, "es"
    )
    text = _text(pdf)

    expected_order = [
        "Lucía Fernández Ortega",
        "Ingeniera de software backend",
        "lucia.fernandez@example.com",
        "Perfil",
        "Experiencia",
        "Ingeniera de software sénior",
        "Migré el cobro con tarjeta",
        "Mentora de tres personas",
        "Desarrolladora backend",
        "Reescribí el buscador",
        "Formación",
        "Grado en Ingeniería Informática",
        "Proyectos",
        "Certificaciones",
        "Habilidades",
        "PostgreSQL",
        "Idiomas",
        "Valenciano",
    ]
    positions = [text.find(fragment) for fragment in expected_order]
    assert -1 not in positions, [f for f, p in zip(expected_order, positions) if p < 0]
    assert positions == sorted(positions), text


@pytest.mark.asyncio
async def test_an_unknown_design_or_language_is_rejected():
    service = CvRenderService(WeasyPrintRenderer())

    with pytest.raises(AppException) as unknown:
        await service.render(sample_snapshot(), "../classic", "es")
    with pytest.raises(AppException) as language:
        await service.render(sample_snapshot(), "classic", "fr")

    assert unknown.value.code == "unknown_design"
    assert language.value.code == "design_language_unavailable"
