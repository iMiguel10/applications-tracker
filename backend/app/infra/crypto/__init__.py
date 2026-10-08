"""Cifrado de las claves de API de los usuarios (ia.md §7): `MultiFernet` con las
claves maestras de `AI_KEYS_ENCRYPTION_KEYS`. Cifra siempre con la primera y
descifra con cualquiera, para poder rotarlas sin perder nada."""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class KeyCipherError(Exception):
    """Un texto cifrado que ninguna clave maestra descifra. No lleva el texto."""


class KeyCipher:
    def __init__(self, master_keys: list[str]) -> None:
        if not master_keys:
            raise ValueError("Hace falta al menos una clave maestra")
        self._fernet = MultiFernet([Fernet(key.encode()) for key in master_keys])

    def encrypt(self, secret: str) -> bytes:
        return self._fernet.encrypt(secret.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken:
            raise KeyCipherError("No se pudo descifrar la clave") from None

    def rotate(self, ciphertext: bytes) -> bytes:
        """El mismo secreto, cifrado con la primera clave maestra."""
        try:
            return self._fernet.rotate(ciphertext)
        except InvalidToken:
            raise KeyCipherError("No se pudo descifrar la clave") from None

    def __repr__(self) -> str:
        return "KeyCipher(...)"


def parse_master_keys(raw: str) -> list[str]:
    """`AI_KEYS_ENCRYPTION_KEYS`: claves Fernet separadas por comas, la nueva primero."""
    return [key.strip() for key in raw.split(",") if key.strip()]


def generate_master_key() -> str:
    return Fernet.generate_key().decode()
