"""Los casos de la evaluación (`cases/*.json`): un perfil inventado, una oferta y
lo que se espera. Se convierten en el mismo `AiProfile` que la aplicación lee de
la base de datos, con UUID nuevos en cada carga."""

import json
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from app.domain.ai import AiEntry, AiLanguage, AiProfile, AiSkill
from app.domain.profile import EntryKind

CASES_DIR = Path(__file__).parent / "cases"


@dataclass(frozen=True)
class EvalCase:
    name: str
    description: str
    language: str
    # "proposal": debe salir una propuesta; "rejected": la oferta no da (RF-119).
    expect: Literal["proposal", "rejected"]
    position_title: str
    company: str
    job_description: str
    # Textos del perfil que no vienen al caso y no deberían aparecer.
    irrelevant: tuple[str, ...]
    profile: AiProfile


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def parse_case(name: str, data: dict[str, Any]) -> EvalCase:
    raw = data["profile"]
    entries = [
        AiEntry(
            id=uuid.uuid4(),
            kind=EntryKind(item["kind"]),
            title=item["title"],
            organization=item.get("organization"),
            start_date=_date(item.get("start_date")),
            end_date=_date(item.get("end_date")),
            is_current=bool(item.get("is_current", False)),
            description=item.get("description"),
            bullets=[(uuid.uuid4(), text) for text in item.get("bullets", [])],
        )
        for item in raw["entries"]
    ]
    profile = AiProfile(
        headline=raw.get("headline"),
        summary=raw.get("summary"),
        entries=entries,
        skills=[
            AiSkill(
                id=uuid.uuid4(),
                name=item["name"],
                category=item.get("category"),
                level=item.get("level"),
            )
            for item in raw.get("skills", [])
        ],
        languages=[
            AiLanguage(id=uuid.uuid4(), language=item["language"], level=item["level"])
            for item in raw.get("languages", [])
        ],
    )
    return EvalCase(
        name=name,
        description=data["description"],
        language=data["language"],
        expect=data["expect"],
        position_title=data["position_title"],
        company=data["company"],
        job_description=data["job_description"],
        irrelevant=tuple(data.get("irrelevant", [])),
        profile=profile,
    )


def load_cases(only: set[str] | None = None) -> list[EvalCase]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        if only and path.stem not in only:
            continue
        cases.append(parse_case(path.stem, json.loads(path.read_text("utf-8"))))
    return cases
