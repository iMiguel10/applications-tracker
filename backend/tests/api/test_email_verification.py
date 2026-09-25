"""Verificación de email contra el core real (autenticación §8: T12, T13, T14).

La API encola; aquí se ejecuta a mano el service del trabajo con
`RecordingEmailSender` para leer el enlace. `require_verified_email` todavía no la
usa ningún endpoint (las funciones con coste llegan en F12+), así que se prueba en
una app mínima con el mismo middleware y la misma dependencia.
"""

import uuid
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe.emailverification.asyncio import (
    create_email_verification_token,
    verify_email_using_token,
)
from supertokens_python.recipe.emailverification.interfaces import (
    CreateEmailVerificationTokenOkResult,
)
from supertokens_python.types import RecipeUserId

from app.api.v1.deps import require_verified_email
from app.core.config import settings
from app.core.exception_handlers import app_exception_handler
from app.core.exceptions import AppException
from app.db.session import get_db
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import EnqueuedJob, InMemoryJobQueue
from app.jobs.auth_emails import SEND_VERIFICATION_EMAIL
from app.main import app
from app.schemas.user import CurrentUser
from app.services.auth_email_service import AuthEmailService
from tests.auth_helpers import BASE_URL, HEADERS, PASSWORD, form

EP = {"rid": "emailpassword"}
EV = {"rid": "emailverification"}


def _verification_jobs() -> list[EnqueuedJob]:
    queue = app.state.job_queue
    assert isinstance(queue, InMemoryJobQueue)
    return [job for job in queue.jobs if job.job == SEND_VERIFICATION_EMAIL]


async def _signup(client: AsyncClient, **headers: str) -> tuple[str, str]:
    email = f"verify-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/signup",
        json=form(email=email, password=PASSWORD),
        headers=EP | headers,
    )
    body = response.json()
    assert body["status"] == "OK"
    return email, body["user"]["id"]


async def _link_from_job(db_session: AsyncSession, job: EnqueuedJob) -> str | None:
    """Hace lo que haría el worker y devuelve el enlace del email (None si no
    se envió nada)."""
    sender = RecordingEmailSender()
    await AuthEmailService(db_session, email_sender=sender).send_verification(
        supertokens_user_id=str(job.kwargs["supertokens_user_id"]),
        tenant_id=str(job.kwargs["tenant_id"]),
        language_hint=None,
    )
    if not sender.sent:
        return None
    return next(
        line for line in sender.sent[0].text.splitlines() if "verify-email" in line
    )


async def _verify(client: AsyncClient, link: str) -> httpx.Response:
    token = parse_qs(urlparse(link).query)["token"][0]
    return await client.post(
        "/auth/user/email/verify",
        json={"method": "token", "token": token},
        headers=EV,
    )


# App mínima con una "función con coste": el mismo middleware de SuperTokens, la
# misma dependencia y el mismo manejo de AppException que la app real.
costly_app = FastAPI()
costly_app.add_middleware(get_middleware())
costly_app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]


@costly_app.get("/costly")
async def costly(
    current_user: CurrentUser = Depends(require_verified_email),
) -> dict[str, str]:
    return {"user_id": str(current_user.id)}


@pytest_asyncio.fixture
async def costly_client(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente de la app mínima. Las cookies de sesión se copian en cada prueba
    DESPUÉS de registrarse: httpx copia el tarro al crear el cliente."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    costly_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=costly_app),
        base_url=BASE_URL,
        headers=HEADERS,
    ) as client:
        yield client
    costly_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_signup_enqueues_the_verification_email_with_ids_only(
    real_auth_client: AsyncClient,
):
    # RF-05: lo dispara el backend al registrarse, sin depender del frontend.
    _, user_id = await _signup(real_auth_client, **{"Accept-Language": "en"})

    [job] = _verification_jobs()
    assert job.max_attempts == 1
    # Sin el enlace: su token verificaría el email y Valkey guarda los trabajos
    # en disco.
    assert job.kwargs == {
        "supertokens_user_id": user_id,
        "tenant_id": "public",
        "language_hint": "en",
    }


@pytest.mark.asyncio
async def test_link_points_to_website_domain_and_works_once(
    real_auth_client: AsyncClient, db_session: AsyncSession
):
    await _signup(real_auth_client)
    [job] = _verification_jobs()

    link = await _link_from_job(db_session, job)

    # T14.
    assert link is not None
    assert link.startswith(f"{settings.website_domain}/verify-email?token=")
    assert "tenantId=public" in link
    assert (await _verify(real_auth_client, link)).json()["status"] == "OK"
    second = await _verify(real_auth_client, link)
    assert second.json()["status"] == "EMAIL_VERIFICATION_INVALID_TOKEN_ERROR"


@pytest.mark.asyncio
async def test_resend_enqueues_again_until_verified(
    real_auth_client: AsyncClient, db_session: AsyncSession
):
    await _signup(real_auth_client)
    [signup_job] = _verification_jobs()

    resend = await real_auth_client.post("/auth/user/email/verify/token", headers=EV)

    assert resend.json()["status"] == "OK"
    assert len(_verification_jobs()) == 2

    link = await _link_from_job(db_session, signup_job)
    assert link is not None
    await _verify(real_auth_client, link)

    # Ya verificado: el SDK no reenvía, y un trabajo que llegase tarde no envía nada.
    after = await real_auth_client.post("/auth/user/email/verify/token", headers=EV)
    assert after.json()["status"] == "EMAIL_ALREADY_VERIFIED_ERROR"
    assert len(_verification_jobs()) == 2
    assert await _link_from_job(db_session, _verification_jobs()[1]) is None


@pytest.mark.asyncio
async def test_unverified_email_blocks_costly_functions_only(
    real_auth_client: AsyncClient, costly_client: AsyncClient
):
    # T13: OPTIONAL. La función con coste responde 403 con código estable; el resto
    # de la API sigue funcionando con la misma sesión.
    await _signup(real_auth_client)
    costly_client.cookies = httpx.Cookies(real_auth_client.cookies)

    costly_response = await costly_client.get("/costly")
    me = await real_auth_client.get("/api/v1/me")

    assert costly_response.status_code == 403
    assert costly_response.json()["code"] == "email_not_verified"
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_verified_elsewhere_is_accepted_with_the_old_token(
    real_auth_client: AsyncClient, costly_client: AsyncClient
):
    # T12: el access token se emitió con "no verificado". Se verifica por otra vía
    # (como desde el móvil: directamente en el core, sin tocar esta sesión) y la
    # función con coste funciona sin renovar la sesión.
    email, user_id = await _signup(real_auth_client)
    token = await create_email_verification_token(
        "public", RecipeUserId(user_id), email
    )
    assert isinstance(token, CreateEmailVerificationTokenOkResult)
    await verify_email_using_token("public", token.token)
    costly_client.cookies = httpx.Cookies(real_auth_client.cookies)

    response = await costly_client.get("/costly")

    assert response.status_code == 200
