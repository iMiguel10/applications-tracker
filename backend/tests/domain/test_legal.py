import pytest

from app.domain.legal import backup_retention_days, legal_configured


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("Ana García", "privacidad@example.com", True),
        ("Ana García", None, False),
        (None, "privacidad@example.com", False),
        ("  ", "privacidad@example.com", False),
        ("Ana García", " ", False),
    ],
)
def test_legal_configured_needs_name_and_contact(
    name: str | None, email: str | None, expected: bool
) -> None:
    assert legal_configured(name, email) is expected


def test_backup_retention_days() -> None:
    assert backup_retention_days(7, 4) == 35
    assert backup_retention_days(3, 0) == 3
