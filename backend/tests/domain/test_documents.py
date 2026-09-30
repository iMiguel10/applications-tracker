import uuid

import pytest

from app.domain.documents import (
    DEFAULT_NAME,
    NAME_MAX_LENGTH,
    content_disposition,
    sanitize_name,
    storage_key,
    user_prefix,
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


def test_content_disposition_sends_ascii_and_utf8_names() -> None:
    # D8: la cabecera solo admite ASCII. NFKD deja "curriculum", no "currculum".
    header = content_disposition("currículum.pdf", attachment=True)

    assert header == (
        "attachment; filename=\"curriculum.pdf\"; filename*=UTF-8''curr%C3%ADculum.pdf"
    )


def test_content_disposition_inline_always_ends_in_pdf_and_escapes_quotes() -> None:
    header = content_disposition('mi "cv"', attachment=False)

    assert header == (
        "inline; filename=\"mi cv.pdf\"; filename*=UTF-8''mi%20%22cv%22.pdf"
    )


def test_user_prefix_has_no_trailing_slash() -> None:
    # delete_prefix rechaza "users/<id>/" (segmento vacío): con la barra, borrar la
    # cuenta dejaba sus ficheros en disco sin que fallara nada visible.
    user_id = uuid.uuid4()

    assert user_prefix(user_id) == f"users/{user_id}"
