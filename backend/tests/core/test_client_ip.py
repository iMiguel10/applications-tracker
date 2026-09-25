import pytest

from app.core.client_ip import client_ip, parse_trusted_proxies

PROXY = parse_trusted_proxies("10.0.0.0/8, 192.168.1.5")


@pytest.mark.parametrize(
    ("peer", "forwarded_for", "trusted", "expected"),
    [
        # Sin proxy: la IP de la conexión.
        ("203.0.113.7", None, (), "203.0.113.7"),
        # L5: X-Forwarded-For desde alguien que no es un proxy de confianza se
        # ignora; si no, cada intento podría llegar con una IP inventada.
        ("203.0.113.7", "1.2.3.4", PROXY, "203.0.113.7"),
        ("203.0.113.7", "1.2.3.4", (), "203.0.113.7"),
        # Detrás del proxy propio: el cliente que vio el proxy.
        ("10.0.0.2", "198.51.100.9", PROXY, "198.51.100.9"),
        # Lo de la izquierda lo escribe el cliente: se toma el primero no fiable
        # empezando por la derecha.
        ("10.0.0.2", "6.6.6.6, 198.51.100.9", PROXY, "198.51.100.9"),
        ("10.0.0.2", "198.51.100.9, 192.168.1.5", PROXY, "198.51.100.9"),
        (None, None, (), "unknown"),
    ],
)
def test_client_ip(
    peer: str | None,
    forwarded_for: str | None,
    trusted: tuple,
    expected: str,  # type: ignore[type-arg]
):
    assert client_ip(peer, forwarded_for, trusted) == expected
