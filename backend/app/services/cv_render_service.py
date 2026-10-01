from app.core.exceptions import AppException
from app.domain.cv import CvDesign, CvSnapshot, template_context
from app.infra.pdf import PdfRenderer
from app.infra.pdf.designs import CvDesignCatalog


class CvRenderService:
    """Maqueta la foto fija de un CV con un diseño y un idioma de etiquetas
    (RF-103…106). Se usa en el `worker`, nunca dentro de una petición (RNF-12)."""

    def __init__(
        self, renderer: PdfRenderer, catalog: CvDesignCatalog | None = None
    ) -> None:
        self.renderer = renderer
        self.catalog = catalog or CvDesignCatalog()

    def designs(self) -> dict[str, CvDesign]:
        return self.catalog.designs()

    def design(self, key: str, language: str) -> CvDesign:
        """El diseño, si existe y tiene etiquetas en ese idioma; si no, 422."""
        design = self.catalog.designs().get(key)
        if design is None:
            raise AppException("Unknown design", status_code=422, code="unknown_design")
        if language not in design.languages:
            raise AppException(
                "The design is not available in that language",
                status_code=422,
                code="design_language_unavailable",
            )
        return design

    async def render(
        self, snapshot: CvSnapshot, design_key: str, language: str
    ) -> bytes:
        design = self.design(design_key, language)
        context = template_context(snapshot, self.catalog.labels(language), language)
        return await self.renderer.render(self.catalog.design_dir(design.key), context)
