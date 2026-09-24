"""Constantes y ayudas de las pruebas que hablan con el core real de SuperTokens
(supertokens-test). El cliente es el fixture `real_auth_client` de conftest.py."""

# Mismo sitio que WEBSITE_DOMAIN (localhost): con otro host, SuperTokens exigiría
# cookies SameSite=None + HTTPS (autenticacion.md §5).
BASE_URL = "http://localhost:8000"
# Como el navegador: supertokens-web-js envía st-auth-mode: cookie en cada petición.
# Sin esa cabecera, el login devolvería los tokens en cabeceras (decisión 0003).
HEADERS = {"Origin": "http://localhost:5173", "st-auth-mode": "cookie"}
PASSWORD = "secreto123"


def form(**fields: str) -> dict[str, list[dict[str, str]]]:
    """Cuerpo de los formularios de SuperTokens: `form(email=…, password=…)`."""
    return {
        "formFields": [{"id": key, "value": value} for key, value in fields.items()]
    }
