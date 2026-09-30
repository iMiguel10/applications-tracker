from datetime import UTC, datetime

import pytest

from app.domain.dates import format_local_datetime
from app.domain.user import Language

# 2026-10-05 07:30 UTC es lunes; en Madrid (CEST, +2) son las 09:30.
INSTANT = datetime(2026, 10, 5, 7, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (Language.ES, "lunes, 5 de octubre de 2026, 09:30"),
        (Language.EN, "Monday, October 5, 2026, 09:30"),
    ],
)
def test_formats_in_the_users_zone_and_language(language: Language, expected: str):
    assert format_local_datetime(INSTANT, "Europe/Madrid", language) == expected


def test_the_local_day_can_differ_from_the_utc_day():
    # A las 03:30 UTC del lunes, en Los Ángeles (-7) aún es domingo por la noche.
    early = datetime(2026, 10, 5, 3, 30, tzinfo=UTC)

    assert format_local_datetime(early, "America/Los_Angeles", Language.ES) == (
        "domingo, 4 de octubre de 2026, 20:30"
    )


def test_winter_time_is_applied_after_the_change():
    # En diciembre Madrid va a +1: nada de desfases fijos (A39).
    winter = datetime(2026, 12, 7, 7, 30, tzinfo=UTC)

    assert format_local_datetime(winter, "Europe/Madrid", Language.ES) == (
        "lunes, 7 de diciembre de 2026, 08:30"
    )


def test_without_a_zone_it_says_the_time_is_utc():
    assert format_local_datetime(INSTANT, None, Language.EN) == (
        "Monday, October 5, 2026, 07:30 (UTC)"
    )
