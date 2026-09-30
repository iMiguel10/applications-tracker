import uuid

import pytest

from app.domain.documents import (
    DEFAULT_NAME,
    NAME_MAX_LENGTH,
    sanitize_name,
    storage_key,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CV backend.pdf", "CV backend.pdf"),
        ("currículum.pdf", "currículum.pdf"),
        # Ruta que mandan algunos navegadores, o un cliente malicioso.
        ("C:\\fakepath\\cv.pdf", "cv.pdf"),
        ("../../etc/passwd", "passwd"),
        # Controles e invisibles: el override de dirección haría que
        # "cv\u202efdp.exe" se viera como "cvexe.pdf".
        ("cv\u202efdp.exe", "cv fdp.exe"),
        ("línea\nnueva\t.pdf", "línea nueva .pdf"),
        ("  mucho    espacio .pdf ", "mucho espacio .pdf"),
        ("", DEFAULT_NAME),
        (None, DEFAULT_NAME),
        ("..", DEFAULT_NAME),
        ("\u200b\u200b", DEFAULT_NAME),
    ],
)
def test_sanitize_name(raw: str | None, expected: str) -> None:
    assert sanitize_name(raw) == expected


def test_a_long_name_is_cut_keeping_the_extension() -> None:
    name = sanitize_name("a" * 500 + ".pdf")

    assert len(name) == NAME_MAX_LENGTH
    assert name.endswith("a.pdf")


def test_storage_key_is_built_by_the_server_from_ids_only() -> None:
    user_id, document_id = uuid.uuid4(), uuid.uuid4()

    assert storage_key(user_id, document_id) == (
        f"users/{user_id}/documents/{document_id}.pdf"
    )
