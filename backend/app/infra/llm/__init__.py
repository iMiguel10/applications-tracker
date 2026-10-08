"""IA: una interfaz propia con un adaptador por proveedor (A31, ia.md §2)."""

from dataclasses import dataclass

from app.core.config import Settings
from app.domain.ai import AiProvider
from app.infra.llm.anthropic import AnthropicProvider
from app.infra.llm.base import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMInvalidOutputError,
    LLMProvider,
    LLMQuotaError,
    LLMRejectedError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)
from app.infra.llm.groq import GroqProvider
from app.infra.llm.ollama import OllamaProvider
from app.infra.llm.openai import OpenAIProvider
from app.infra.llm.schema import strict_json_schema

__all__ = [
    "LLMAuthError",
    "LLMError",
    "LLMFinish",
    "LLMInvalidOutputError",
    "LLMProvider",
    "LLMQuotaError",
    "LLMRejectedError",
    "LLMRequest",
    "LLMResponse",
    "LLMUnavailableError",
    "PlatformModel",
    "build_llm_providers",
    "platform_model",
    "strict_json_schema",
]


@dataclass(frozen=True)
class PlatformModel:
    """Con qué se sirven los usos gratuitos (decisión 0017): proveedor, modelo y
    clave de la plataforma, y su precio para estimar el coste de cada propuesta."""

    provider: AiProvider
    model: str
    # None con un proveedor sin clave (Ollama).
    api_key: str | None
    input_usd_per_mtok: float
    output_usd_per_mtok: float

    def __repr__(self) -> str:
        # La clave nunca en un log ni en un traceback con variables.
        return f"PlatformModel(provider={self.provider!s}, model={self.model!r})"


def platform_model(settings: Settings) -> PlatformModel | None:
    """El modelo de la plataforma, o None si la instalación no tiene uso gratuito."""
    if settings.ai_platform_provider is None:
        return None
    # Lo garantiza el validador de Settings.
    assert settings.ai_platform_model
    return PlatformModel(
        provider=settings.ai_platform_provider,
        model=settings.ai_platform_model,
        api_key=settings.ai_platform_api_key,
        input_usd_per_mtok=settings.ai_platform_input_usd_per_mtok,
        output_usd_per_mtok=settings.ai_platform_output_usd_per_mtok,
    )


def build_llm_providers(settings: Settings) -> dict[AiProvider, LLMProvider]:
    """Un adaptador por proveedor. Solo lo llaman quienes cablean (el worker,
    deps.py, los scripts), nunca un service. El de Ollama, solo si quien despliega
    da su dirección."""
    timeout = settings.ai_request_timeout_seconds
    providers: dict[AiProvider, LLMProvider] = {
        AiProvider.ANTHROPIC: AnthropicProvider(timeout_seconds=timeout),
        AiProvider.OPENAI: OpenAIProvider(timeout_seconds=timeout),
        AiProvider.GROQ: GroqProvider(timeout_seconds=timeout),
    }
    if settings.ai_ollama_base_url:
        providers[AiProvider.OLLAMA] = OllamaProvider(
            base_url=settings.ai_ollama_base_url,
            timeout_seconds=timeout,
            context_tokens=settings.ai_ollama_context_tokens,
        )
    return providers
