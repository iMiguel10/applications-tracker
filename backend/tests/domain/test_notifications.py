import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.notifications import (
    MAX_DELIVERY_ATTEMPTS,
    interview_from_key,
    interview_key,
    next_attempt_at,
    reminder_due_key,
    reminder_id_from_key,
)

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


def test_reminder_key_round_trip():
    reminder_id = uuid.uuid4()

    assert reminder_id_from_key(reminder_due_key(reminder_id)) == reminder_id


@pytest.mark.parametrize(
    "key", ["interview:123", "reminder:no-es-un-uuid", f"xreminder:{uuid.uuid4()}"]
)
def test_other_keys_are_not_reminders(key: str):
    assert reminder_id_from_key(key) is None


def test_interview_key_carries_the_time_and_round_trips():
    interview_id = uuid.uuid4()
    at = datetime(2031, 3, 10, 9, 30, 15, 500_000, tzinfo=UTC)

    key = interview_key(interview_id, at)

    assert key == f"interview:{interview_id}:{int(at.timestamp())}"
    assert interview_from_key(key) == (interview_id, int(at.timestamp()))


def test_moving_an_interview_changes_its_key():
    # B8: un aviso nuevo, no un duplicado bloqueado por el de la hora antigua.
    interview_id = uuid.uuid4()
    at = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)

    assert interview_key(interview_id, at) != interview_key(
        interview_id, at + timedelta(hours=1)
    )


@pytest.mark.parametrize(
    "key", [f"reminder:{uuid.uuid4()}", "interview:x:1", f"interview:{uuid.uuid4()}:x"]
)
def test_other_keys_are_not_interviews(key: str):
    assert interview_from_key(key) is None
