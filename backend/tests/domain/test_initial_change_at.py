"""Fecha del cambio inicial de una solicitud enviada (decisión 0015). Reglas puras."""

from datetime import UTC, date, datetime

from app.domain.application_status import initial_change_at

# 1 de octubre a las 15:30 UTC: en Madrid (UTC+2) son las 17:30 del mismo día.
NOW = datetime(2026, 10, 1, 15, 30, tzinfo=UTC)


def test_past_day_keeps_the_current_time_of_day_in_the_user_zone():
    at = initial_change_at(date(2026, 9, 20), NOW, "Europe/Madrid")

    assert at == datetime(2026, 9, 20, 15, 30, tzinfo=UTC)
    assert at.tzinfo is UTC


def test_without_zone_the_day_is_taken_in_utc():
    assert initial_change_at(date(2026, 9, 20), NOW, None) == datetime(
        2026, 9, 20, 15, 30, tzinfo=UTC
    )


def test_unknown_zone_falls_back_to_utc():
    assert initial_change_at(date(2026, 9, 20), NOW, "Mars/Olympus") == datetime(
        2026, 9, 20, 15, 30, tzinfo=UTC
    )


def test_today_future_or_no_date_is_now():
    assert initial_change_at(date(2026, 10, 1), NOW, "Europe/Madrid") == NOW
    assert initial_change_at(date(2026, 12, 24), NOW, "Europe/Madrid") == NOW
    assert initial_change_at(None, NOW, "Europe/Madrid") == NOW


def test_today_is_the_user_day_not_the_utc_one():
    # 23:30 UTC del 1 de octubre: en Tokio ya es día 2. Para quien vive allí, el
    # día 1 es ayer y el cambio va a ayer a la misma hora local.
    late = datetime(2026, 10, 1, 23, 30, tzinfo=UTC)

    assert initial_change_at(date(2026, 10, 1), late, "Asia/Tokyo") == datetime(
        2026, 9, 30, 23, 30, tzinfo=UTC
    )
    # Y en Nueva York (19:30 del día 1) sigue siendo hoy: ahora.
    assert initial_change_at(date(2026, 10, 1), late, "America/New_York") == late


def test_never_lands_in_the_future():
    for zone in ("Pacific/Kiritimati", "Pacific/Pago_Pago", "Europe/Madrid", None):
        for day in (date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2)):
            assert initial_change_at(day, NOW, zone) <= NOW
