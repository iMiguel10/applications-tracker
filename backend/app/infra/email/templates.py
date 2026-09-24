from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "email"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


class EmailTemplates:
    """Plantillas de email de `templates/email/<tipo>/<idioma>.{txt,html}` (A36).

    El asunto vive en la plantilla de texto (`{% set subject = … %}`), junto al
    resto de textos de ese idioma: así una traducción está entera en un sitio.
    """

    def __init__(self, directory: Path = EMAIL_TEMPLATES_DIR) -> None:
        self._environment = Environment(
            loader=FileSystemLoader(directory),
            # Escapa solo el HTML: en el texto plano, un `&` debe seguir siendo `&`.
            autoescape=select_autoescape(enabled_extensions=("html",)),
            # Una variable mal escrita falla en vez de salir vacía en un email real.
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def render(
        self, kind: str, language: str, context: Mapping[str, Any]
    ) -> RenderedEmail:
        text_module = self._environment.get_template(
            f"{kind}/{language}.txt"
        ).make_module(dict(context))
        # Las variables `{% set %}` de primer nivel se exportan al módulo.
        subject = str(vars(text_module)["subject"]).strip()
        html = self._environment.get_template(f"{kind}/{language}.html").render(
            **context, subject=subject, language=language
        )
        return RenderedEmail(subject=subject, text=str(text_module), html=html)
