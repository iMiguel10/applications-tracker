from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol


class PdfRenderer(Protocol):
    """Genera un PDF a partir de un diseño: una carpeta con `template.html`
    (Jinja2), sus estilos y sus fuentes (A25). `template` elige otra plantilla de
    la misma carpeta: la carta (`letter.html`) usa las fuentes y el estilo del CV. El service prepara `context` con
    los datos ya decididos; la plantilla solo los presenta.

    Se usa en el `worker`, nunca dentro de una petición (RNF-12).
    """

    async def render(
        self,
        template_dir: Path,
        context: Mapping[str, Any],
        template: str = "template.html",
    ) -> bytes: ...
