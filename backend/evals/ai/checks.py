"""Comprobaciones automáticas de la evaluación, sobre lo que la validación no ve
(ia.md §5): la validación garantiza que cada logro y cada fuente existen en el
perfil, no que el texto sea fiel. Son pistas para la revisión a ojo, no un juicio:
un número nuevo puede venir de reescribir bien ("cinco" → "5")."""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.domain.ai import AiProfile, CoverLetterProposal, CvProposal

# Un id corto colado en el texto ("[e1.b2]", "(s3)", "e1"): saldría en el PDF si
# clean_text no lo quitara, y dice cómo de bien sigue el modelo las instrucciones.
_SHORT_ID = re.compile(r"(?<![\w.])[escl]\d+(?:\.b\d+)?(?![\w])")
# Cifras: "40", "40 %", "6", "2.5", "1,5".
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
# Los campos de texto libre de las respuestas (cv/v2 y cover_letter/v1).
_TEXT_FIELDS = {"summary", "text", "greeting", "closing", "note"}


@dataclass
class Checks:
    # Ids cortos escritos dentro del texto de la respuesta cruda.
    ids_in_text: int = 0
    # Logros reescritos que perdieron una cifra del original.
    changed_figures: list[str] = field(default_factory=list)
    # Cifras de la propuesta que no están ni en el perfil ni en la oferta.
    new_numbers: list[str] = field(default_factory=list)
    # Textos que no vienen al caso y aparecen en la propuesta.
    irrelevant: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (
            self.ids_in_text
            or self.changed_figures
            or self.new_numbers
            or self.irrelevant
        )


def numbers(text: str) -> set[str]:
    return {match.replace(",", ".") for match in _NUMBER.findall(text)}


def raw_text_fields(raw: str) -> list[str]:
    """Los textos libres de la respuesta tal como la dio el modelo, antes de
    limpiarla. Una respuesta que no es JSON no tiene ninguno."""
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    found: list[str] = []

    def walk(value: object, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, child_key)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and key in _TEXT_FIELDS:
            found.append(value)

    walk(data)
    return found


def count_ids_in_text(raw: str) -> int:
    return sum(len(_SHORT_ID.findall(text)) for text in raw_text_fields(raw))


def proposal_texts(proposal: CvProposal | CoverLetterProposal) -> list[str]:
    if isinstance(proposal, CvProposal):
        return [proposal.summary] + [
            bullet.text for item in proposal.experiences for bullet in item.bullets
        ]
    return (
        [proposal.greeting]
        + [paragraph.text for paragraph in proposal.paragraphs]
        + [proposal.closing]
    )


def profile_texts(profile: AiProfile) -> list[str]:
    texts = [profile.headline or "", profile.summary or ""]
    for entry in profile.entries:
        texts += [entry.title, entry.organization or "", entry.description or ""]
        texts += [text for _, text in entry.bullets]
        for value in (entry.start_date, entry.end_date):
            if value:
                texts.append(str(value.year))
    texts += [skill.name for skill in profile.skills]
    texts += [f"{item.language} {item.level}" for item in profile.languages]
    return texts


def check_proposal(
    proposal: CvProposal | CoverLetterProposal,
    profile: AiProfile,
    *,
    raw: str,
    job_description: str,
    irrelevant: Iterable[str],
) -> Checks:
    checks = Checks(ids_in_text=count_ids_in_text(raw))
    texts = proposal_texts(proposal)

    if isinstance(proposal, CvProposal):
        originals = {
            bullet_id: text
            for entry in profile.entries
            for bullet_id, text in entry.bullets
        }
        for item in proposal.experiences:
            for bullet in item.bullets:
                lost = numbers(originals.get(bullet.bullet_id, "")) - numbers(
                    bullet.text
                )
                if lost:
                    checks.changed_figures.append(
                        f"{bullet.text} (faltan: {', '.join(sorted(lost))})"
                    )

    known = numbers(" ".join(profile_texts(profile))) | numbers(job_description)
    found = set().union(*(numbers(text) for text in texts)) if texts else set()
    checks.new_numbers = sorted(found - known)

    joined = " ".join(texts).lower()
    checks.irrelevant = [item for item in irrelevant if item.lower() in joined]
    return checks
