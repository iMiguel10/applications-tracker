import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
@pytest.mark.parametrize(("smtp_host", "expected"), [("mailpit", True), (None, False)])
async def test_meta_reports_whether_email_is_enabled(
    anonymous_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    smtp_host: str | None,
    expected: bool,
):
    monkeypatch.setattr(settings, "smtp_host", smtp_host)

    response = await anonymous_client.get("/api/v1/meta")

    assert response.status_code == 200
    # Igualdad exacta (L10): un campo nuevo obliga a revisar esta prueba, y con
    # ella que lo público siga siendo solo configuración, nada de usuarios.
    assert response.json() == {"email_enabled": expected}
