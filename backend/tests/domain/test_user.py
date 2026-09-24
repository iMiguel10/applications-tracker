import pytest

from app.domain.user import Language, language_from_accept_language


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("", None),
        ("en-GB,en;q=0.9", Language.EN),
        ("es-ES", Language.ES),
        # El orden lo decide `q`, no la posición.
        ("es;q=0.4, en;q=0.8", Language.EN),
        # Salta los idiomas no soportados.
        ("fr-FR,fr;q=0.9,es;q=0.5", Language.ES),
        ("de, fr", None),
        # q=0 significa "no lo quiero".
        ("en;q=0, es;q=0.1", Language.ES),
        # Un `q` mal formado se ignora sin romper el resto.
        ("en;q=abc, es", Language.ES),
        ("*", None),
    ],
)
def test_language_from_accept_language(header: str | None, expected: Language | None):
    assert language_from_accept_language(header) == expected
