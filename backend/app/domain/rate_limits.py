"""Reglas de rate limiting (RNF-04, límites y abuso §2). Reglas puras, sin I/O.

Formato de la librería `limits`: "<cantidad>/<periodo>". Son valores de partida,
que se ajustarán con uso real. Al superarlos se **frena** (hay que esperar), nunca
se bloquea la cuenta: si 10 intentos fallidos la bloquearan, cualquiera podría
dejar sin acceso a otra persona sabiendo solo su email.
"""

from dataclasses import dataclass
from enum import StrEnum


class RateKey(StrEnum):
    """Por qué se agrupan las peticiones."""

    IP = "ip"
    EMAIL = "email"
    USER = "user"


@dataclass(frozen=True)
class RateRule:
    name: str
    limit: str
    key: RateKey


SIGNIN_PER_IP = RateRule("signin", "10/minute", RateKey.IP)
SIGNIN_PER_EMAIL = RateRule("signin", "10/hour", RateKey.EMAIL)
SIGNUP_PER_IP = RateRule("signup", "5/hour", RateKey.IP)
PASSWORD_RESET_PER_EMAIL = RateRule("password_reset", "3/hour", RateKey.EMAIL)
PASSWORD_RESET_PER_IP = RateRule("password_reset", "10/hour", RateKey.IP)
RESEND_VERIFICATION_PER_USER = RateRule("resend_verification", "3/hour", RateKey.USER)
# Límite general de toda la API con sesión (añadido en F11 a petición del
# usuario): nadie lo nota usando la aplicación, pero frena un script que la machaque.
API_PER_USER = RateRule("api", "600/minute", RateKey.USER)

# Rutas /auth/* de SuperTokens (POST) y sus reglas. Las sirve el middleware de
# SuperTokens, no nuestros endpoints: las limita api/auth_rate_limit.py.
AUTH_RULES: dict[str, tuple[RateRule, ...]] = {
    "/auth/signin": (SIGNIN_PER_IP, SIGNIN_PER_EMAIL),
    "/auth/signup": (SIGNUP_PER_IP,),
    "/auth/user/password/reset/token": (
        PASSWORD_RESET_PER_EMAIL,
        PASSWORD_RESET_PER_IP,
    ),
    "/auth/user/email/verify/token": (RESEND_VERIFICATION_PER_USER,),
}
