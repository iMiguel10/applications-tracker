from pathlib import Path

import pytest
from jinja2 import UndefinedError

from app.domain.user import Language
from app.infra.email.templates import EMAIL_TEMPLATES_DIR, EmailTemplates

LINK = "http://localhost:5173/reset-password?token=abc&tenantId=public"


@pytest.mark.parametrize("language", list(Language))
def test_every_email_kind_exists_in_every_language(language: Language):
    # Un idioma sin plantilla haría fallar el envío en el worker, no en el arranque.
    kinds = [path for path in EMAIL_TEMPLATES_DIR.iterdir() if path.is_dir()]
    assert kinds
    for kind in kinds:
        assert (kind / f"{language}.txt").is_file(), kind.name
        assert (kind / f"{language}.html").is_file(), kind.name


@pytest.mark.parametrize(
    ("language", "subject"),
    [
        (Language.ES, "Restablece tu contraseña de Applications Tracker"),
        (Language.EN, "Reset your Applications Tracker password"),
    ],
)
def test_password_reset_renders_subject_text_and_html(language: Language, subject: str):
    rendered = EmailTemplates().render(
        "password_reset", language, {"link": LINK, "expires_in_minutes": 60}
    )

    assert rendered.subject == subject
    # El asunto no se cuela en el cuerpo del texto.
    assert subject not in rendered.text
    assert LINK in rendered.text
    assert "60" in rendered.text
    assert f'<html lang="{language}">' in rendered.html


def test_html_is_escaped_and_text_is_not():
    rendered = EmailTemplates().render(
        "password_reset", "es", {"link": LINK, "expires_in_minutes": 60}
    )

    # El `&` del enlace: literal en el texto plano, escapado en el HTML.
    assert "token=abc&tenantId=public" in rendered.text
    assert "token=abc&amp;tenantId=public" in rendered.html


def test_missing_variable_fails_instead_of_rendering_empty(tmp_path: Path):
    kind = tmp_path / "demo"
    kind.mkdir()
    (kind / "es.txt").write_text('{% set subject = "Hola" %}{{ missing }}')
    (kind / "es.html").write_text("<p>ok</p>")

    with pytest.raises(UndefinedError):
        EmailTemplates(tmp_path).render("demo", "es", {})
