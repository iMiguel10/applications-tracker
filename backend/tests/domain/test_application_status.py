"""Tabla de transiciones (especificación §6). Reglas puras: sin BD ni fixtures."""

import pytest

from app.domain.application_status import (
    ApplicationStatus,
    allowed_transitions,
    is_transition_allowed,
)

FINAL_STATUSES = [
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
]


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (ApplicationStatus.SAVED, ApplicationStatus.APPLIED),
        (ApplicationStatus.SAVED, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.APPLIED, ApplicationStatus.SCREENING),
        (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING),  # salto permitido
        (ApplicationStatus.APPLIED, ApplicationStatus.REJECTED),
        (ApplicationStatus.APPLIED, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.SCREENING, ApplicationStatus.INTERVIEWING),
        (ApplicationStatus.SCREENING, ApplicationStatus.REJECTED),
        (ApplicationStatus.SCREENING, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFER),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.REJECTED),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.OFFER, ApplicationStatus.ACCEPTED),
        (ApplicationStatus.OFFER, ApplicationStatus.REJECTED),
        (ApplicationStatus.OFFER, ApplicationStatus.WITHDRAWN),
    ],
)
def test_allowed_transitions(
    from_status: ApplicationStatus, to_status: ApplicationStatus
):
    assert is_transition_allowed(from_status, to_status)
    assert to_status in allowed_transitions(from_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (ApplicationStatus.APPLIED, ApplicationStatus.SAVED),  # retroceder
        (ApplicationStatus.REJECTED, ApplicationStatus.OFFER),  # salir de un final
        (ApplicationStatus.SAVED, ApplicationStatus.INTERVIEWING),  # sin aplicar
        (ApplicationStatus.SAVED, ApplicationStatus.SAVED),  # quedarse quieto
        (ApplicationStatus.OFFER, ApplicationStatus.SCREENING),
    ],
)
def test_forbidden_transitions(
    from_status: ApplicationStatus, to_status: ApplicationStatus
):
    assert not is_transition_allowed(from_status, to_status)
    assert to_status not in allowed_transitions(from_status)


@pytest.mark.parametrize("status", FINAL_STATUSES)
def test_final_statuses_have_no_transitions(status: ApplicationStatus):
    assert allowed_transitions(status) == ()
