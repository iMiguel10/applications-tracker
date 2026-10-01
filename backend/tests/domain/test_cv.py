"""Foto fija y presentación de un CV (F14, RF-103, RF-106, A27)."""

import uuid
from datetime import date

from app.domain.cv import (
    CvSection,
    CvSelection,
    SnapshotBullet,
    SnapshotContact,
    SnapshotEntry,
    SnapshotLanguage,
    SnapshotSkill,
    build_snapshot,
    display_url,
    format_period,
    group_skills,
)
from app.domain.profile import EntryKind
from app.infra.pdf.designs import CvDesignCatalog

LABELS = CvDesignCatalog().labels("es")


def _entry(
    title: str = "Puesto",
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    is_current: bool = False,
    bullets: list[SnapshotBullet] | None = None,
) -> SnapshotEntry:
    return SnapshotEntry(
        id=uuid.uuid4(),
        title=title,
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
        bullets=bullets or [],
    )


def test_the_snapshot_keeps_what_was_chosen_in_profile_order():
    dropped_bullet = SnapshotBullet(id=uuid.uuid4(), text="Se quita")
    job = _entry(
        bullets=[SnapshotBullet(id=uuid.uuid4(), text="Se queda"), dropped_bullet]
    )
    other_job = _entry("Excluida")
    degree = _entry("Grado")
    selection = CvSelection(
        sections=frozenset(
            {CvSection.EXPERIENCE, CvSection.EDUCATION, CvSection.SKILLS}
        ),
        excluded_ids=frozenset({other_job.id, dropped_bullet.id}),
    )

    snapshot = build_snapshot(
        contact=SnapshotContact(full_name="Ana"),
        summary="Resumen",
        entries=[job, other_job, degree],
        entry_kinds={
            job.id: EntryKind.EXPERIENCE,
            other_job.id: EntryKind.EXPERIENCE,
            degree.id: EntryKind.EDUCATION,
        },
        skills=[SnapshotSkill(id=uuid.uuid4(), name="SQL")],
        languages=[SnapshotLanguage(id=uuid.uuid4(), language="Inglés", level="c1")],
        selection=selection,
    )

    assert snapshot.contact.full_name == "Ana"
    assert snapshot.summary is None
    assert [s.section for s in snapshot.entry_sections] == [
        CvSection.EXPERIENCE,
        CvSection.EDUCATION,
    ]
    [kept_job] = snapshot.entry_sections[0].entries
    assert [bullet.text for bullet in kept_job.bullets] == ["Se queda"]
    assert [skill.name for skill in snapshot.skills] == ["SQL"]
    assert snapshot.languages == []


def test_an_empty_section_does_not_appear():
    snapshot = build_snapshot(
        contact=SnapshotContact(),
        summary=None,
        entries=[],
        entry_kinds={},
        skills=[],
        languages=[],
        selection=CvSelection(),
    )

    assert snapshot.entry_sections == []


def test_periods_show_month_and_year_in_the_labels_language():
    assert (
        format_period(_entry(start_date=date(2021, 3, 1), is_current=True), LABELS)
        == "mar 2021 – actualidad"
    )
    assert (
        format_period(
            _entry(start_date=date(2017, 9, 1), end_date=date(2021, 2, 1)), LABELS
        )
        == "sep 2017 – feb 2021"
    )
    # Una certificación: empieza y acaba el mismo mes.
    same = date(2022, 11, 1)
    assert format_period(_entry(start_date=same, end_date=same), LABELS) == "nov 2022"
    assert format_period(_entry(), LABELS) is None


def test_skills_are_grouped_by_category_with_the_uncategorised_last():
    skills = [
        SnapshotSkill(id=uuid.uuid4(), name="Mentoría"),
        SnapshotSkill(
            id=uuid.uuid4(), name="Python", category="Lenguajes", level="expert"
        ),
        SnapshotSkill(id=uuid.uuid4(), name="Docker", category="Plataforma"),
        SnapshotSkill(id=uuid.uuid4(), name="Go", category="Lenguajes"),
    ]

    groups = group_skills(skills, LABELS)

    assert [(g["category"], [s["name"] for s in g["skills"]]) for g in groups] == [
        ("Lenguajes", ["Python", "Go"]),
        ("Plataforma", ["Docker"]),
        (None, ["Mentoría"]),
    ]
    assert groups[0]["skills"][0]["level"] == "Experto"


def test_links_are_shown_without_scheme_www_or_trailing_slash():
    assert display_url("https://www.linkedin.com/in/ana/") == "linkedin.com/in/ana"
    assert display_url("http://ana.dev") == "ana.dev"


def test_both_label_files_have_the_same_keys():
    catalog = CvDesignCatalog()

    def keys(value: object, prefix: str = "") -> set[str]:
        if isinstance(value, dict):
            return {f"{prefix}{key}" for key in value} | {
                k
                for key, inner in value.items()
                for k in keys(inner, f"{prefix}{key}.")
            }
        return set()

    assert keys(catalog.labels("es")) == keys(catalog.labels("en"))
    assert len(catalog.labels("es")["months"]) == 12
