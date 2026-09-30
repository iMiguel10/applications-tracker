from datetime import UTC, datetime, timedelta

from app.domain.notifications import MAX_DELIVERY_ATTEMPTS, next_attempt_at

FAILED_AT = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)


def test_retries_wait_longer_each_time_and_stop_after_the_last_attempt():
    first = next_attempt_at(1, FAILED_AT)
    second = next_attempt_at(2, FAILED_AT)

    assert first is not None and second is not None
    assert FAILED_AT < first < second
    assert next_attempt_at(MAX_DELIVERY_ATTEMPTS, FAILED_AT) is None


def test_first_retry_is_minutes_away_not_immediate():
    # Un reintento inmediato repetiría el mismo fallo (el SMTP sigue caído).
    first = next_attempt_at(1, FAILED_AT)

    assert first is not None
    assert first - FAILED_AT >= timedelta(minutes=1)
