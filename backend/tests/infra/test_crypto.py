"""Cifrado de las claves de API de los usuarios (ia.md §7): MultiFernet, rotación
y que una clave maestra mal configurada no deja arrancar."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.infra.crypto import (
    KeyCipher,
    KeyCipherError,
    generate_master_key,
    parse_master_keys,
)

SECRET = "sk-ant-secreta-1234567890"


def test_encrypts_and_decrypts_without_keeping_the_secret_visible() -> None:
    cipher = KeyCipher([generate_master_key()])

    ciphertext = cipher.encrypt(SECRET)

    assert SECRET.encode() not in ciphertext
    assert cipher.decrypt(ciphertext) == SECRET
    assert "ciphertext" not in repr(cipher) and SECRET not in repr(cipher)


def test_rotation_reencrypts_with_the_new_key_and_old_ones_still_decrypt() -> None:
    old, new = generate_master_key(), generate_master_key()
    stored = KeyCipher([old]).encrypt(SECRET)
    during = KeyCipher([new, old])

    rotated = during.rotate(stored)

    # Mientras la antigua siga en la lista, lo guardado se descifra (no hay que
    # parar nada); tras rotar, basta con la nueva.
    assert during.decrypt(stored) == SECRET
    assert KeyCipher([new]).decrypt(rotated) == SECRET
    with pytest.raises(KeyCipherError):
        KeyCipher([new]).decrypt(stored)


def test_a_wrong_master_key_says_so_without_the_ciphertext() -> None:
    stored = KeyCipher([generate_master_key()]).encrypt(SECRET)

    with pytest.raises(KeyCipherError) as caught:
        KeyCipher([generate_master_key()]).decrypt(stored)

    assert caught.value.__cause__ is None
    assert stored.decode() not in str(caught.value)


def test_master_keys_are_a_clean_ordered_list() -> None:
    assert parse_master_keys(" a , ,b ") == ["a", "b"]
    assert parse_master_keys("") == []


def make_settings(**overrides: Any) -> Settings:
    return Settings(**(settings.model_dump() | overrides))


def test_a_malformed_master_key_does_not_start() -> None:
    with pytest.raises(ValidationError, match="AI_KEYS_ENCRYPTION_KEYS"):
        make_settings(ai_keys_encryption_keys="no-es-una-clave-fernet")


def test_without_master_keys_there_are_no_own_keys() -> None:
    assert make_settings(ai_keys_encryption_keys="").ai_own_keys_enabled is False
    assert make_settings(
        ai_keys_encryption_keys=generate_master_key()
    ).ai_own_keys_enabled
