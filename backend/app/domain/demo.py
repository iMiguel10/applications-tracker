"""La cuenta de demostración: límites con los que nace cada día (ver
`services/demo_account_service.py`). Reglas puras, sin I/O."""

from app.domain.limits import LimitKey

DEMO_LIMITS: dict[LimitKey, int] = {
    LimitKey.APPLICATIONS: 15,
    LimitKey.COMPANIES: 10,
    LimitKey.REMINDERS: 10,
    LimitKey.DOCUMENTS: 3,
    LimitKey.STORAGE_BYTES: 2 * 1024 * 1024,
    # Sin IA: cada propuesta cuesta (o satura al Ollama propio) y la contraseña es
    # pública.
    LimitKey.AI_CV_PROPOSALS: 0,
    LimitKey.AI_COVER_LETTER_PROPOSALS: 0,
}
