"""Reglas del dashboard (RF-60…66). Reglas puras, sin I/O.

Distingue dos tipos de métrica: las que retratan el estado **actual** (recuento por
estado, solicitudes sin actividad) excluyen las archivadas, porque archivar es la
señal del usuario de "ya no sigo esto". Las que retratan **lo ocurrido** (envíos por
semana, tasa de respuesta) incluyen también las archivadas: que una solicitud se
archivara después no borra que se enviara esa semana o que llegara a `screening`.
"""

from app.domain.application_status import ApplicationStatus

# RF-64: estados en los que la solicitud espera una respuesta. `saved` queda fuera
# (aún no se ha enviado, no hay nadie a quien esperar); los estados finales también.
WAITING_STATUSES = frozenset(
    {
        ApplicationStatus.APPLIED,
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.OFFER,
    }
)

# RF-64: días sin `last_activity_at` para considerar una solicitud "sin actividad".
STALE_AFTER_DAYS = 14

# RF-62: a partir de qué `to_status` del historial se considera que la empresa
# respondió ("screening o más allá"), sin importar a dónde fue después.
RESPONSE_REACHED_STATUSES = frozenset(
    {
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.OFFER,
        ApplicationStatus.ACCEPTED,
    }
)

# RF-66: con menos solicitudes enviadas que esto, no se muestra el porcentaje.
MIN_SAMPLE_FOR_RATE = 5

# RF-61: tamaño de la ventana de envíos semanales.
WEEKS_OF_HISTORY = 12

# Tamaño de cada lista de vistazo del dashboard (próximas entrevistas, recordatorios
# pendientes, solicitudes sin actividad). El listado completo vive en su propia
# página; el dashboard solo da un vistazo con enlace a "ver todos".
WIDGET_LIST_LIMIT = 5
