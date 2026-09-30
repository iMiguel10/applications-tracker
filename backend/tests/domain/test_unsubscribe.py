import uuid

import pytest

from app.domain.notifications import NotificationKind
from app.domain.unsubscribe import (
    PREFERENCE_FOR_KIND,
    unsubscribe_token,
    verify_unsubscribe_token,
)
from app.models.user import User

SECRET = "s" * 40
USER = uuid.uuid4()
KIND = NotificationKind.REMINDER_DUE


def test_a_signed_token_names_its_user_and_kind():
    token = unsubscribe_token(USER, KIND, SECRET)

    assert verify_unsubscribe_token(token, SECRET) == (USER, KIND)


def test_changing_the_user_or_the_kind_breaks_the_signature():
    # B10: un token firmado para un usuario no sirve para otro.
    _, kind, signature = unsubscribe_token(USER, KIND, SECRET).split(".")
    other_user = f"{uuid.uuid4().hex}.{kind}.{signature}"
    other_kind = f"{USER.hex}.{NotificationKind.WEEKLY_DIGEST}.{signature}"

    assert verify_unsubscribe_token(other_user, SECRET) is None
    assert verify_unsubscribe_token(other_kind, SECRET) is None


def test_a_token_from_another_installation_is_not_valid():
    token = unsubscribe_token(USER, KIND, SECRET)

    assert verify_unsubscribe_token(token, "o" * 40) is None


@pytest.mark.parametrize(
    "token", ["", "a.b", "a.b.c.d", "no-es-un-uuid.reminder_due.x", "..."]
)
def test_malformed_tokens_are_rejected(token: str):
    assert verify_unsubscribe_token(token, SECRET) is None


def test_every_kind_has_a_preference_to_turn_it_off():
    assert set(PREFERENCE_FOR_KIND) == set(NotificationKind)
    assert all(hasattr(User, field) for field in PREFERENCE_FOR_KIND.values())
