"""Cuándo toca el resumen semanal (RF-82, segundo plano §6: B9)."""

from datetime import UTC, datetime

import pytest

from app.domain.notifications import digest_key_if_due


@pytest.mark.parametrize(
    ("now", "timezone", "expected"),
    [
        # Nueva York cambia al horario de verano el domingo 9 de marzo de 2031:
        # el lunes 10, las 8:00 locales son las 12:00 UTC (−4), no las 13:00.
        (datetime(2031, 3, 10, 11, 59, tzinfo=UTC), "America/New_York", None),
        (
            datetime(2031, 3, 10, 12, 0, tzinfo=UTC),
            "America/New_York",
            "digest:2031-W11",
        ),
        # Madrid cambia el domingo 30 de marzo: el lunes 31, las 8:00 son las 6:00 UTC.
        (datetime(2031, 3, 31, 5, 59, tzinfo=UTC), "Europe/Madrid", None),
        (datetime(2031, 3, 31, 6, 0, tzinfo=UTC), "Europe/Madrid", "digest:2031-W14"),
        # Y la semana anterior al cambio, Madrid aún va a +1: las 8:00 son las 7:00.
        (datetime(2031, 3, 24, 6, 59, tzinfo=UTC), "Europe/Madrid", None),
        (datetime(2031, 3, 24, 7, 0, tzinfo=UTC), "Europe/Madrid", "digest:2031-W13"),
    ],
)
def test_monday_at_eight_local_time_also_on_the_clock_change(
    now: datetime, timezone: str, expected: str | None
):
    assert digest_key_if_due(now, timezone) == expected


def test_the_whole_monday_after_eight_is_the_same_week():
    # El barrido pasa cada hora: todas las pasadas del lunes dan la misma clave.
    keys = {
        digest_key_if_due(datetime(2031, 3, 10, hour, 0, tzinfo=UTC), "UTC")
        for hour in range(8, 24)
    }

    assert keys == {"digest:2031-W11"}


@pytest.mark.parametrize("day", [9, 11, 16])
def test_not_on_other_days(day: int):
    assert digest_key_if_due(datetime(2031, 3, day, 10, 0, tzinfo=UTC), "UTC") is None


def test_the_local_monday_can_be_sunday_in_utc():
    # En Auckland (+13 en marzo) el lunes a las 8:00 es aún domingo en UTC.
    now = datetime(2031, 3, 9, 19, 0, tzinfo=UTC)

    assert digest_key_if_due(now, "Pacific/Auckland") == "digest:2031-W11"


def test_the_iso_week_can_belong_to_the_previous_year():
    # El lunes 29 de diciembre de 2031 abre la semana 1 de 2032.
    assert (
        digest_key_if_due(datetime(2031, 12, 29, 9, 0, tzinfo=UTC), None)
        == "digest:2032-W01"
    )
