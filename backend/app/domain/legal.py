"""Páginas legales de cada instalación (issue #3, decisión 0026).

Los textos los monta el frontend con los datos del responsable (variables
`LEGAL_*`) y con lo que la instalación tiene activo. Aquí, lo que decide el
backend: la versión vigente que cada persona acepta y cuándo cuenta como
configurada.
"""

# Versión de los textos legales. Se cambia cuando cambia su contenido de forma que
# haya que volver a aceptarlos (una finalidad o un destinatario nuevos), no por una
# corrección de estilo: al cambiarla, todas las cuentas vuelven a ver la pantalla
# de aceptación.
LEGAL_VERSION = "2026-10-20"
LEGAL_VERSION_MAX_LENGTH = 20


def legal_configured(operator_name: str | None, contact_email: str | None) -> bool:
    """Sin un responsable y un contacto, las páginas no pueden decir quién trata los
    datos: la instalación se trata como de uso personal (sin enlaces ni
    aceptación)."""
    return bool(operator_name and operator_name.strip()) and bool(
        contact_email and contact_email.strip()
    )


def backup_retention_days(keep_daily: int, keep_weekly: int) -> int:
    """Cuánto tarda, como mucho, en desaparecer de las copias lo que se borra: las
    diarias más una semana por cada semanal (la retención de deploy/backup)."""
    return keep_daily + 7 * keep_weekly
