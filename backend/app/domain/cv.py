"""CVs generados desde el perfil (F14, RF-103…106, A25, A27). Reglas puras, sin I/O.

Un CV se genera en dos tiempos. Al pedirlo se toma una **foto fija** del perfil con
lo elegido (`CvSnapshot`, que se guarda en `documents.content`): el CV que se envió
no cambia aunque luego se edite el perfil. Después, el `worker` la maqueta con un
diseño y un idioma de etiquetas. Aquí vive lo que no depende ni de la BD ni de
WeasyPrint: qué entra en la foto y cómo se presenta cada dato.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from app.domain.profile import EntryKind


class CvSection(StrEnum):
    """Secciones del CV, en el orden en que salen."""

    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECT = "project"
    CERTIFICATION = "certification"
    SKILLS = "skills"
    LANGUAGES = "languages"


# Las secciones que son entradas del perfil, en su orden en el CV.
ENTRY_SECTIONS: tuple[tuple[CvSection, EntryKind], ...] = (
    (CvSection.EXPERIENCE, EntryKind.EXPERIENCE),
    (CvSection.EDUCATION, EntryKind.EDUCATION),
    (CvSection.PROJECT, EntryKind.PROJECT),
    (CvSection.CERTIFICATION, EntryKind.CERTIFICATION),
)


@dataclass(frozen=True)
class CvDesign:
    """Un diseño de CV: una carpeta `templates/cv/<key>/` con su `manifest.json`
    (A25). Un diseño nuevo es una carpeta nueva, sin tocar código (RF-104)."""

    key: str
    names: Mapping[str, str]
    descriptions: Mapping[str, str]
    languages: tuple[str, ...]
    # RF-105: texto seleccionable y en orden de lectura. Un diseño gráfico (dos
    # columnas, texto en bandas de color) lo declara falso y la interfaz lo avisa.
    ats_friendly: bool


# --- La foto fija (A27) ----------------------------------------------------------
# Lleva los ids del perfil: en F15, la propuesta de la IA los referencia.


class SnapshotLink(BaseModel):
    label: str
    url: str


class SnapshotContact(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[SnapshotLink] = []


class SnapshotBullet(BaseModel):
    id: uuid.UUID
    text: str


class SnapshotEntry(BaseModel):
    id: uuid.UUID
    title: str
    organization: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    bullets: list[SnapshotBullet] = []


class SnapshotEntrySection(BaseModel):
    section: CvSection
    entries: list[SnapshotEntry]


class SnapshotSkill(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None = None
    level: str | None = None


class SnapshotLanguage(BaseModel):
    id: uuid.UUID
    language: str
    level: str


class CvSnapshot(BaseModel):
    """Lo que se maqueta, tal como era al pedirlo. Una sección vacía no sale."""

    contact: SnapshotContact
    summary: str | None = None
    entry_sections: list[SnapshotEntrySection] = []
    skills: list[SnapshotSkill] = []
    languages: list[SnapshotLanguage] = []


# --- Qué entra en la foto (RF-103) ------------------------------------------------


@dataclass(frozen=True)
class CvSelection:
    """Qué incluir: las secciones elegidas y, dentro de ellas, todo salvo los
    elementos excluidos (entradas, logros, habilidades o idiomas, por id)."""

    sections: frozenset[CvSection] = frozenset(CvSection)
    excluded_ids: frozenset[uuid.UUID] = frozenset()

    def includes(self, section: CvSection) -> bool:
        return section in self.sections

    def keeps(self, item_id: uuid.UUID) -> bool:
        return item_id not in self.excluded_ids


def build_snapshot(
    *,
    contact: SnapshotContact,
    summary: str | None,
    entries: Sequence[SnapshotEntry],
    entry_kinds: Mapping[uuid.UUID, EntryKind],
    skills: Sequence[SnapshotSkill],
    languages: Sequence[SnapshotLanguage],
    selection: CvSelection,
) -> CvSnapshot:
    """La foto fija con lo elegido, en el orden del perfil. Los datos de contacto
    entran siempre: sin ellos el CV no dice de quién es."""
    entry_sections: list[SnapshotEntrySection] = []
    for section, kind in ENTRY_SECTIONS:
        if not selection.includes(section):
            continue
        kept = [
            entry.model_copy(
                update={
                    "bullets": [
                        bullet for bullet in entry.bullets if selection.keeps(bullet.id)
                    ]
                }
            )
            for entry in entries
            if entry_kinds[entry.id] == kind and selection.keeps(entry.id)
        ]
        if kept:
            entry_sections.append(SnapshotEntrySection(section=section, entries=kept))

    return CvSnapshot(
        contact=contact,
        summary=summary if selection.includes(CvSection.SUMMARY) else None,
        entry_sections=entry_sections,
        skills=[
            skill
            for skill in skills
            if selection.includes(CvSection.SKILLS) and selection.keeps(skill.id)
        ],
        languages=[
            language
            for language in languages
            if selection.includes(CvSection.LANGUAGES) and selection.keeps(language.id)
        ],
    )


# --- Cómo se presenta (lo que recibe la plantilla) ---------------------------------


def format_month(value: date, labels: Mapping[str, Any]) -> str:
    """ "mar 2021": el mes con su abreviatura en el idioma de las etiquetas. Sin
    depender de la configuración regional del sistema (la imagen no la trae)."""
    return f"{labels['months'][value.month - 1]} {value.year}"


def format_period(entry: SnapshotEntry, labels: Mapping[str, Any]) -> str | None:
    """ "mar 2021 – actualidad": siempre mes y año, como se guardaron, y una sola
    fecha si empieza y acaba el mismo mes.
    `None` si la entrada no tiene fechas."""
    start = format_month(entry.start_date, labels) if entry.start_date else None
    if entry.is_current:
        end: str | None = labels["present"]
    elif entry.end_date:
        end = format_month(entry.end_date, labels)
    else:
        end = None
    if start and end:
        return start if start == end else f"{start} – {end}"
    return start or end


def group_skills(
    skills: Sequence[SnapshotSkill], labels: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Las habilidades agrupadas por categoría, en el orden en que aparece cada
    categoría por primera vez; las que no tienen categoría, al final."""
    groups: dict[str | None, list[dict[str, Any]]] = {}
    for skill in skills:
        groups.setdefault(skill.category, []).append(
            {
                "name": skill.name,
                "level": labels["skill_levels"][skill.level] if skill.level else None,
                "level_rank": _SKILL_RANK.get(skill.level or "", 0),
            }
        )
    named: list[dict[str, Any]] = [
        {"category": category, "skills": items}
        for category, items in groups.items()
        if category is not None
    ]
    if None in groups:
        named.append({"category": None, "skills": groups[None]})
    return named


# Posición del nivel en su escala, para diseños que lo dibujan (barras, puntos).
_SKILL_RANK = {"basic": 1, "intermediate": 2, "advanced": 3, "expert": 4}
_LANGUAGE_RANK = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6, "native": 7}
SKILL_RANK_MAX = 4
LANGUAGE_RANK_MAX = 7


def template_context(
    snapshot: CvSnapshot, labels: Mapping[str, Any], language: str
) -> dict[str, Any]:
    """Todo lo que usa una plantilla, ya decidido: la plantilla solo presenta.

    Con `StrictUndefined`, una plantilla que pida algo que no está aquí falla al
    maquetar en vez de dejar un hueco: por eso todas reciben exactamente esto."""
    return {
        "language": language,
        "labels": labels,
        "contact": snapshot.contact.model_dump(exclude={"links"}),
        "links": [
            {"label": link.label, "url": link.url, "display": display_url(link.url)}
            for link in snapshot.contact.links
        ],
        "summary": snapshot.summary,
        "entry_sections": [
            {
                "key": section.section.value,
                "title": labels["sections"][section.section.value],
                "entries": [
                    {
                        "title": entry.title,
                        "organization": entry.organization,
                        "location": entry.location,
                        "period": format_period(entry, labels),
                        "description": entry.description,
                        "bullets": [bullet.text for bullet in entry.bullets],
                    }
                    for entry in section.entries
                ],
            }
            for section in snapshot.entry_sections
        ],
        "skill_groups": group_skills(snapshot.skills, labels),
        "languages": [
            {
                "language": item.language,
                "level": labels["language_levels"][item.level],
                "level_rank": _LANGUAGE_RANK[item.level],
            }
            for item in snapshot.languages
        ],
        "skill_rank_max": SKILL_RANK_MAX,
        "language_rank_max": LANGUAGE_RANK_MAX,
    }


def display_url(url: str) -> str:
    """La dirección como se lee en un CV: sin `https://`, `www.` ni barra final
    (el enlace sigue llevando la dirección completa)."""
    shown = url.split("://", 1)[-1]
    shown = shown.removeprefix("www.")
    return shown.rstrip("/")
