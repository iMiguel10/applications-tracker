import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.domain.ai import PERSONAL_PROVIDERS, AiProvider
from app.infra.crypto import KeyCipher, KeyCipherError, parse_master_keys
from app.infra.llm import (
    LLMAuthError,
    LLMError,
    LLMProvider,
    LLMQuotaError,
    LLMRejectedError,
)
from app.repositories.ai_provider_key_repository import AiProviderKeyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai import AiKeyRead, AiKeysRead, AiProviderOption

logger = logging.getLogger(__name__)

# Una clave de API real tiene decenas de caracteres; esto solo descarta lo que
# claramente no lo es antes de llamar al proveedor.
API_KEY_MIN_LENGTH = 8
API_KEY_MAX_LENGTH = 500


def offered_personal_providers(config: Settings) -> list[AiProvider]:
    """Con qué proveedores se puede usar una clave propia en esta instalación: los
    que tienen modelos en la lista (`AI_*_MODELS`), si hay claves maestras para
    cifrarlas (0017)."""
    if not config.ai_own_keys_enabled:
        return []
    return [provider for provider in PERSONAL_PROVIDERS if config.ai_models(provider)]


@dataclass(frozen=True)
class ActiveKey:
    """La clave propia con la que se usará la IA: proveedor y modelo. La clave en
    claro no está aquí: solo la descifra el worker al llamar."""

    provider: AiProvider
    model: str


class AiKeyService:
    """Las claves de API propias de un usuario (RF-151, RF-153, ia.md §7): se
    validan con una llamada mínima al proveedor, se guardan cifradas y nunca
    vuelven al cliente. Guardar una la deja activa; se puede volver a los usos
    gratuitos.

    Los adaptadores se usan aquí solo para validar (`check_access`), sin generar."""

    def __init__(
        self,
        session: AsyncSession,
        config: Settings = settings,
        *,
        providers: Mapping[AiProvider, LLMProvider] | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.providers = providers or {}
        self.keys = AiProviderKeyRepository(session)
        self.users = UserRepository(session)

    def _cipher(self) -> KeyCipher:
        if not self.config.ai_own_keys_enabled:
            raise ConflictError("Own AI keys are not enabled", code="ai_keys_disabled")
        return KeyCipher(parse_master_keys(self.config.ai_keys_encryption_keys))

    def _offered(self, provider: AiProvider) -> None:
        if provider not in offered_personal_providers(self.config):
            raise AppException(
                "AI provider not offered",
                status_code=422,
                code="ai_provider_not_offered",
            )

    def _allowed_model(self, provider: AiProvider, model: str | None) -> str:
        models = self.config.ai_models(provider)
        if model is None:
            return models[0]
        if model not in models:
            raise AppException(
                "Model not allowed", status_code=422, code="ai_model_not_allowed"
            )
        return model

    # --- Consultar ------------------------------------------------------------

    async def overview(self, user_id: uuid.UUID) -> AiKeysRead:
        saved = {AiProvider(key.provider): key for key in await self.keys.list(user_id)}
        user = await self.users.get_by_id(user_id)
        active = user.ai_provider if user else None
        options: list[AiProviderOption] = []
        for provider in offered_personal_providers(self.config):
            models = self.config.ai_models(provider)
            key = saved.get(provider)
            options.append(
                AiProviderOption(
                    provider=provider,
                    models=models,
                    key=AiKeyRead(
                        model=key.model,
                        last4=key.last4,
                        validated_at=key.validated_at,
                        model_allowed=key.model in models,
                    )
                    if key
                    else None,
                )
            )
        return AiKeysRead(
            own_keys_enabled=self.config.ai_own_keys_enabled,
            providers=options,
            active_provider=AiProvider(active) if active else None,
        )

    async def active(self, user_id: uuid.UUID) -> ActiveKey | None:
        """La clave propia activa, o None si se usan los usos gratuitos. Si el
        proveedor dejó de ofrecerse o su modelo se retiró, 409: nunca se pasa en
        silencio a la clave de la plataforma (ia.md §6)."""
        user = await self.users.get_by_id(user_id)
        if user is None or user.ai_provider is None:
            return None
        provider = AiProvider(user.ai_provider)
        key = await self.keys.get(user_id, provider)
        if key is None or provider not in offered_personal_providers(self.config):
            raise ConflictError(
                "The active AI key is not available", code="ai_key_unavailable"
            )
        if key.model not in self.config.ai_models(provider):
            raise ConflictError(
                "The model of the active AI key is no longer allowed",
                code="ai_model_not_allowed",
            )
        return ActiveKey(provider=provider, model=key.model)

    async def decrypt(self, user_id: uuid.UUID, provider: AiProvider) -> str | None:
        """La clave en claro, para la llamada del worker. None si ya no está (se
        borró entre pedir la propuesta y ejecutarla) o no se puede descifrar."""
        key = await self.keys.get(user_id, provider)
        if key is None or not self.config.ai_own_keys_enabled:
            return None
        try:
            return self._cipher().decrypt(key.ciphertext)
        except KeyCipherError:
            # Una clave maestra retirada antes de rotar: el usuario tiene que
            # volver a guardarla.
            logger.error("Clave de IA de %s sin descifrar (%s)", user_id, provider)
            return None

    # --- Cambiar ----------------------------------------------------------------

    async def save(
        self,
        user_id: uuid.UUID,
        provider: AiProvider,
        api_key: str,
        model: str | None,
    ) -> AiKeysRead:
        """Comprueba la clave contra el proveedor (RF-153), la guarda cifrada y la
        deja activa. La comprobación va antes de tocar la BD: nada queda bloqueado
        mientras se espera al proveedor."""
        self._offered(provider)
        chosen = self._allowed_model(provider, model)
        secret = api_key.strip()
        if not API_KEY_MIN_LENGTH <= len(secret) <= API_KEY_MAX_LENGTH:
            raise AppException(
                "That does not look like an API key",
                status_code=422,
                code="ai_key_invalid",
            )
        cipher = self._cipher()
        await self._check(provider, chosen, secret)

        await self.keys.save(
            user_id,
            provider,
            model=chosen,
            ciphertext=cipher.encrypt(secret),
            last4=secret[-4:],
            validated_at=datetime.now(UTC),
        )
        await self._set_active(user_id, provider)
        await self.session.commit()
        return await self.overview(user_id)

    async def change_model(
        self, user_id: uuid.UUID, provider: AiProvider, model: str
    ) -> AiKeysRead:
        """Otro modelo para la misma clave, comprobando que la clave lo tiene."""
        self._offered(provider)
        chosen = self._allowed_model(provider, model)
        if await self.keys.get(user_id, provider) is None:
            raise NotFoundError("AI key")
        secret = await self.decrypt(user_id, provider)
        if secret is None:
            raise ConflictError(
                "The saved AI key cannot be used", code="ai_key_unavailable"
            )
        await self._check(provider, chosen, secret)
        await self.keys.set_model(user_id, provider, chosen)
        await self.session.commit()
        return await self.overview(user_id)

    async def delete(self, user_id: uuid.UUID, provider: AiProvider) -> None:
        """Borra la clave. Si era la activa, se vuelve a los usos gratuitos."""
        if not await self.keys.delete(user_id, provider):
            raise NotFoundError("AI key")
        user = await self.users.get_by_id(user_id)
        if user is not None and user.ai_provider == provider.value:
            await self._set_active(user_id, None)
        await self.session.commit()

    async def set_active(
        self, user_id: uuid.UUID, provider: AiProvider | None
    ) -> AiKeysRead:
        """Elige con qué se usa la IA: una clave guardada o, con None, los usos
        gratuitos de la plataforma."""
        if provider is not None:
            self._offered(provider)
            if await self.keys.get(user_id, provider) is None:
                raise ConflictError(
                    "No AI key for that provider", code="ai_key_missing"
                )
        await self._set_active(user_id, provider)
        await self.session.commit()
        return await self.overview(user_id)

    async def _set_active(
        self, user_id: uuid.UUID, provider: AiProvider | None
    ) -> None:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        user.ai_provider = provider.value if provider else None
        await self.users.save(user)

    async def _check(self, provider: AiProvider, model: str, secret: str) -> None:
        """La llamada mínima al proveedor (RF-153), con sus errores en códigos
        propios. El error del proveedor nunca se propaga (ia.md §7)."""
        adapter = self.providers.get(provider)
        if adapter is None:
            raise ConflictError("AI provider not available", code="ai_unavailable")
        try:
            await adapter.check_access(model=model, api_key=secret)
        except LLMAuthError:
            raise AppException(
                "The provider rejected the key", status_code=422, code="ai_key_invalid"
            ) from None
        except LLMRejectedError:
            raise AppException(
                "The key cannot use that model",
                status_code=422,
                code="ai_model_unavailable",
            ) from None
        except LLMQuotaError:
            raise AppException(
                "The provider account has no quota left",
                status_code=422,
                code="ai_provider_quota",
            ) from None
        except LLMError:
            raise AppException(
                "The AI provider could not be reached",
                status_code=503,
                code="ai_provider_unavailable",
            ) from None
