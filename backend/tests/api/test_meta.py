import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.domain.legal import LEGAL_VERSION


@pytest.mark.asyncio
@pytest.mark.parametrize(("smtp_host", "expected"), [("mailpit", True), (None, False)])
async def test_meta_reports_whether_email_is_enabled(
    anonymous_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    smtp_host: str | None,
    expected: bool,
):
    monkeypatch.setattr(settings, "smtp_host", smtp_host)
    monkeypatch.setattr(settings, "legal_operator_name", None)
    monkeypatch.setattr(settings, "ai_platform_provider", None)
    monkeypatch.setattr(settings, "ai_keys_encryption_keys", "")

    response = await anonymous_client.get("/api/v1/meta")

    assert response.status_code == 200
    # Igualdad exacta (L10): un campo nuevo obliga a revisar esta prueba, y con
    # ella que lo público siga siendo solo configuración, nada de usuarios.
    assert response.json() == {
        "email_enabled": expected,
        "signup_enabled": True,
        "max_document_bytes": settings.document_max_bytes,
        "legal": {
            "configured": False,
            "version": LEGAL_VERSION,
            "operator_name": None,
            "contact_email": None,
            "address": None,
            "tax_id": None,
            "supervisory_authority": None,
            "ai_platform_provider": None,
            "ai_own_key_providers": [],
            "backup_retention_days": 35,
        },
    }


@pytest.mark.asyncio
async def test_meta_reports_whether_signup_is_open(
    anonymous_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Decisión 0022: el frontend oculta el registro si está cerrado.
    monkeypatch.setattr(settings, "signup_enabled", False)

    response = await anonymous_client.get("/api/v1/meta")

    assert response.json()["signup_enabled"] is False


@pytest.mark.asyncio
async def test_meta_publishes_the_operator_once_configured(
    anonymous_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Issue #3: con nombre y contacto, las páginas legales dicen quién trata los
    # datos y a quién van (la IA de la plataforma, las claves propias).
    monkeypatch.setattr(settings, "legal_operator_name", "Ana García")
    monkeypatch.setattr(settings, "legal_contact_email", "privacidad@example.com")
    monkeypatch.setattr(settings, "legal_address", " ")
    monkeypatch.setattr(settings, "legal_tax_id", "12345678Z")
    monkeypatch.setattr(settings, "legal_supervisory_authority", "CNIL")
    monkeypatch.setattr(settings, "backup_keep_daily", 3)
    monkeypatch.setattr(settings, "backup_keep_weekly", 0)

    legal = (await anonymous_client.get("/api/v1/meta")).json()["legal"]

    assert legal["configured"] is True
    assert legal["operator_name"] == "Ana García"
    assert legal["contact_email"] == "privacidad@example.com"
    assert legal["address"] is None  # en blanco es lo mismo que sin poner
    assert legal["tax_id"] == "12345678Z"
    assert legal["supervisory_authority"] == "CNIL"
    assert legal["backup_retention_days"] == 3


@pytest.mark.asyncio
async def test_meta_without_contact_is_not_configured_and_hides_the_name(
    anonymous_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # A medias no cuenta: unas páginas con nombre y sin forma de contactar no
    # sirven para ejercer ningún derecho.
    monkeypatch.setattr(settings, "legal_operator_name", "Ana García")
    monkeypatch.setattr(settings, "legal_contact_email", None)

    legal = (await anonymous_client.get("/api/v1/meta")).json()["legal"]

    assert legal["configured"] is False
    assert legal["operator_name"] is None
