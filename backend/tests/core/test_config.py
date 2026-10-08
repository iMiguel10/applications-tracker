"""Lectura de la configuración del entorno (`Settings`)."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


def make_settings(**changes: Any) -> Settings:
    return Settings(**(settings.model_dump() | changes))


@pytest.mark.parametrize("value", ["unlimited", "UNLIMITED", " Unlimited "])
def test_the_free_ai_uses_can_be_unlimited(value: str) -> None:
    # 0020: quien despliega puede quitar el tope (pensado para un Ollama propio).
    config = make_settings(
        limit_ai_cv_proposals=value, limit_ai_cover_letter_proposals=value
    )

    assert config.limit_ai_cv_proposals is None
    assert config.limit_ai_cover_letter_proposals is None


def test_the_free_ai_uses_default_to_one_and_accept_a_number() -> None:
    assert Settings.model_fields["limit_ai_cv_proposals"].default == 1
    assert Settings.model_fields["limit_ai_cover_letter_proposals"].default == 1
    assert make_settings(limit_ai_cv_proposals="5").limit_ai_cv_proposals == 5


@pytest.mark.parametrize("value", ["-1", "muchos"])
def test_a_wrong_number_of_free_ai_uses_does_not_start(value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(limit_ai_cv_proposals=value)


@pytest.mark.parametrize("field", ["limit_storage_bytes", "limit_applications"])
def test_the_other_limits_are_never_unlimited_from_the_environment(field: str) -> None:
    # Solo los usos de IA: el almacenamiento tiene tope siempre (F11), y el resto
    # solo admite "sin límite" como excepción de una cuenta.
    with pytest.raises(ValidationError):
        make_settings(**{field: "unlimited"})
