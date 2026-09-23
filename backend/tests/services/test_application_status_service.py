import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.schemas.application_status_change import ApplicationStatusChangeCreate
from app.schemas.user import CurrentUser
from app.services.application_status_service import ApplicationStatusService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_application, make_status_change


@pytest.mark.asyncio
async def test_valid_transition_updates_status_and_appends_history(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    updated = await ApplicationStatusService(db_session).change(
        user.id,
        application.id,
        ApplicationStatusChangeCreate(to_status="screening"),
    )

    assert updated.status == "screening"


@pytest.mark.asyncio
async def test_can_skip_a_status_forward(db_session: AsyncSession, user: CurrentUser):
    # Regla 1 de la especificación §6: no todas las empresas hacen screening.
    application = await make_application(db_session, user.id, status="applied")

    updated = await ApplicationStatusService(db_session).change(
        user.id,
        application.id,
        ApplicationStatusChangeCreate(to_status="interviewing"),
    )

    assert updated.status == "interviewing"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "to_status"),
    [
        ("applied", "saved"),  # retroceder
        ("rejected", "offer"),  # salir de un estado final
        ("saved", "interviewing"),  # entrevistar sin haber aplicado
        ("saved", "saved"),  # quedarse en el mismo estado
    ],
)
async def test_invalid_transition_is_rejected(
    db_session: AsyncSession, user: CurrentUser, status: str, to_status: str
):
    application = await make_application(db_session, user.id, status=status)

    with pytest.raises(ConflictError) as error:
        await ApplicationStatusService(db_session).change(
            user.id, application.id, ApplicationStatusChangeCreate(to_status=to_status)
        )

    assert error.value.code == "invalid_transition"


@pytest.mark.asyncio
async def test_moving_to_applied_without_date_uses_changed_at(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, status="saved", applied_at=None
    )

    # Sin changed_at explícito: la solicitud se creó hace un instante, así que el
    # cambio inicial ya tiene un changed_at de "ahora" y no se puede usar una fecha
    # anterior (ver test_changed_at_earlier_than_last_change_is_rejected).
    updated = await ApplicationStatusService(db_session).change(
        user.id, application.id, ApplicationStatusChangeCreate(to_status="applied")
    )

    assert updated.applied_at == datetime.now(UTC).date()


@pytest.mark.asyncio
async def test_changed_at_in_the_future_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")
    future = datetime.now(UTC) + timedelta(days=1)

    with pytest.raises(AppException) as error:
        await ApplicationStatusService(db_session).change(
            user.id,
            application.id,
            ApplicationStatusChangeCreate(to_status="screening", changed_at=future),
        )

    assert error.value.code == "changed_at_in_future"


@pytest.mark.asyncio
async def test_changed_at_earlier_than_last_change_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")
    now = datetime.now(UTC)
    await make_status_change(
        db_session, application, to_status="applied", changed_at=now
    )
    application.status = "applied"

    with pytest.raises(AppException) as error:
        await ApplicationStatusService(db_session).change(
            user.id,
            application.id,
            ApplicationStatusChangeCreate(
                to_status="screening", changed_at=now - timedelta(days=1)
            ),
        )

    assert error.value.code == "changed_at_before_last_change"


@pytest.mark.asyncio
async def test_change_on_unknown_application_is_not_found(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)

    with pytest.raises(NotFoundError):
        await ApplicationStatusService(db_session).change(
            user.id,
            others_application.id,
            ApplicationStatusChangeCreate(to_status="screening"),
        )


@pytest.mark.asyncio
async def test_undo_restores_the_previous_status_and_removes_the_change(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")
    service = ApplicationStatusService(db_session)
    await service.change(
        user.id, application.id, ApplicationStatusChangeCreate(to_status="screening")
    )

    undone = await service.undo_last(user.id, application.id)

    assert undone.status == "applied"
    history = await ApplicationStatusChangeRepository(db_session).list_for_application(
        user.id, application.id
    )
    assert [change.to_status for change in history] == ["applied"]


@pytest.mark.asyncio
async def test_cannot_undo_the_initial_change(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    with pytest.raises(ConflictError) as error:
        await ApplicationStatusService(db_session).undo_last(user.id, application.id)

    assert error.value.code == "cannot_undo_initial_change"


@pytest.mark.asyncio
async def test_undo_a_specific_past_change_removes_that_one_not_another(
    db_session: AsyncSession, user: CurrentUser
):
    # Registrar un cambio con changed_at pasado no cambia CUÁL es el último por seq
    # (0004): sigue siendo el que se insertó después, no el de fecha más reciente.
    application = await make_application(db_session, user.id, status="saved")
    now = datetime.now(UTC)
    await make_status_change(
        db_session, application, to_status="applied", changed_at=now
    )
    application.status = "applied"
    await make_status_change(
        db_session,
        application,
        to_status="withdrawn",
        changed_at=now - timedelta(days=1),  # fecha declarada, anterior a la anterior
    )
    application.status = "withdrawn"
    await db_session.flush()

    undone = await ApplicationStatusService(db_session).undo_last(
        user.id, application.id
    )

    assert undone.status == "applied"
    history = await ApplicationStatusChangeRepository(db_session).list_for_application(
        user.id, application.id
    )
    assert [change.to_status for change in history] == ["applied", "saved"]


@pytest.mark.asyncio
async def test_status_always_matches_the_last_change_after_change_and_undo(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")
    service = ApplicationStatusService(db_session)

    await service.change(
        user.id, application.id, ApplicationStatusChangeCreate(to_status="screening")
    )
    await service.change(
        user.id,
        application.id,
        ApplicationStatusChangeCreate(to_status="interviewing"),
    )
    updated = await service.undo_last(user.id, application.id)

    history = await ApplicationStatusChangeRepository(db_session).list_for_application(
        user.id, application.id
    )
    assert updated.status == history[0].to_status


@pytest.mark.asyncio
async def test_concurrent_status_changes_never_both_start_from_the_same_state():
    # No se puede usar el fixture db_session: su transacción con savepoint no es
    # visible desde otra conexión, y aquí hacen falta DOS conexiones reales para que
    # el SELECT ... FOR UPDATE de una bloquee de verdad a la otra (arquitectura §8,
    # la trampa del FOR UPDATE). Los datos quedan en db-test: se destruye entera
    # tras la batería (compose.test.yml down -v) y el user_id es único por test.
    async with test_engine.connect() as setup_connection:
        setup_session = AsyncSession(bind=setup_connection, expire_on_commit=False)
        user = await create_test_user(setup_session)
        application = await make_application(setup_session, user.id, status="applied")
        application_id = application.id
        await setup_session.commit()

    async with (
        test_engine.connect() as connection_a,
        test_engine.connect() as connection_b,
    ):
        session_a = AsyncSession(bind=connection_a, expire_on_commit=False)
        session_b = AsyncSession(bind=connection_b, expire_on_commit=False)

        # Las dos parten de "applied" y las dos transiciones son válidas desde ahí:
        # si el FOR UPDATE no sirviera de nada, ambas podrían leer "applied" a la vez
        # e insertar dos cambios con el mismo from_status.
        results = await asyncio.gather(
            ApplicationStatusService(session_a).change(
                user.id,
                application_id,
                ApplicationStatusChangeCreate(to_status="screening"),
            ),
            ApplicationStatusService(session_b).change(
                user.id,
                application_id,
                ApplicationStatusChangeCreate(to_status="withdrawn"),
            ),
            return_exceptions=True,
        )

    errors = [result for result in results if isinstance(result, BaseException)]
    for error in errors:
        assert isinstance(error, ConflictError)
        assert error.code == "invalid_transition"

    async with test_engine.connect() as check_connection:
        check_session = AsyncSession(bind=check_connection, expire_on_commit=False)
        history = await ApplicationStatusChangeRepository(
            check_session
        ).list_for_application(user.id, application_id)

    # Cadena lineal: el from_status de cada cambio es el to_status del siguiente
    # (más antiguo). Si las dos hubieran partido de "applied" a la vez, dos
    # entradas seguidas tendrían from_status="applied".
    for later, earlier in zip(history, history[1:], strict=False):
        assert later.from_status == earlier.to_status
