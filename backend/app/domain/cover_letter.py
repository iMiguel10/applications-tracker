"""La carta de presentación como documento (RF-114): su foto fija y lo que recibe
la plantilla. Se maqueta con el mismo diseño que un CV (una plantilla de carta por
diseño, decisión 0017), en `templates/cv/<diseño>/letter.html`."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.domain.cv import SnapshotContact, display_url

LETTER_TEMPLATE_FILE = "letter.html"


class CoverLetterSnapshot(BaseModel):
    """Lo que dice la carta, fijado al pedir el PDF (A27): si el perfil o la
    solicitud cambian después, la carta no. La fecha va ya escrita, en el idioma de
    la carta y el día de la zona horaria del usuario."""

    contact: SnapshotContact
    company: str
    position: str
    date: str
    greeting: str
    paragraphs: list[str]
    closing: str


def letter_context(
    snapshot: CoverLetterSnapshot, labels: Mapping[str, Any], language: str
) -> dict[str, Any]:
    """Todo lo que usa la plantilla de la carta, ya decidido (como `template_context`
    del CV, con `StrictUndefined`)."""
    return {
        "language": language,
        "labels": labels,
        "contact": snapshot.contact.model_dump(exclude={"links"}),
        "links": [
            {"label": link.label, "url": link.url, "display": display_url(link.url)}
            for link in snapshot.contact.links
        ],
        "company": snapshot.company,
        "subject": labels["letter"]["subject"].format(position=snapshot.position),
        "date": snapshot.date,
        "greeting": snapshot.greeting,
        "paragraphs": snapshot.paragraphs,
        "closing": snapshot.closing,
    }
