from app.core.config import Settings, settings
from app.domain.legal import LEGAL_VERSION, backup_retention_days
from app.infra.llm import platform_model
from app.schemas.meta import LegalRead
from app.services.ai_key_service import offered_personal_providers


def _blank_is_none(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def legal_info(config: Settings = settings) -> LegalRead:
    """Lo que publican las páginas legales (issue #3): el responsable y lo que la
    instalación tiene activo, para que el texto diga a quién van los datos de
    verdad. Sin configurar, sin datos del responsable."""
    configured = config.legal_configured

    def operator(value: str | None) -> str | None:
        return _blank_is_none(value) if configured else None

    platform = platform_model(config)
    return LegalRead(
        configured=configured,
        version=LEGAL_VERSION,
        operator_name=operator(config.legal_operator_name),
        contact_email=operator(config.legal_contact_email),
        address=operator(config.legal_address),
        tax_id=operator(config.legal_tax_id),
        supervisory_authority=_blank_is_none(config.legal_supervisory_authority),
        ai_platform_provider=platform.provider if platform else None,
        ai_own_key_providers=offered_personal_providers(config),
        backup_retention_days=backup_retention_days(
            config.backup_keep_daily, config.backup_keep_weekly
        ),
    )
