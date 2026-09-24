"""Generación de PDF. `PdfRenderer` es la interfaz; la implementación con
WeasyPrint vive en `app.infra.pdf.weasyprint_renderer` y se importa solo donde se cablea
(el worker), para que la API no cargue WeasyPrint sin necesitarlo."""

from app.infra.pdf.base import PdfRenderer

__all__ = ["PdfRenderer"]
