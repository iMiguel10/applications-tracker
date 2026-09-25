"""IP real del cliente para el rate limiting, detrás o no de un proxy."""

import ipaddress
from functools import cache

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@cache
def parse_trusted_proxies(value: str) -> tuple[IPNetwork, ...]:
    """`TRUSTED_PROXIES`: IPs o redes CIDR separadas por comas."""
    return tuple(
        ipaddress.ip_network(item.strip(), strict=False)
        for item in value.split(",")
        if item.strip()
    )


def _is_trusted(address: str, trusted: tuple[IPNetwork, ...]) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in trusted)


def client_ip(
    peer: str | None, forwarded_for: str | None, trusted: tuple[IPNetwork, ...]
) -> str:
    """La IP de la conexión, salvo que venga de un proxy de confianza: entonces, la
    primera de `X-Forwarded-For` empezando por la derecha que no sea de confianza.

    Solo se hace caso a `X-Forwarded-For` si lo añadió un proxy propio. Si no,
    cualquiera podría inventarse una IP distinta en cada intento y esquivar el
    límite (límites y abuso §2). Por la derecha, porque cada proxy añade al final:
    lo de la izquierda lo puede escribir el cliente.
    """
    peer = peer or "unknown"
    if not forwarded_for or not _is_trusted(peer, trusted):
        return peer
    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, trusted):
            return hop
    return hops[0] if hops else peer
