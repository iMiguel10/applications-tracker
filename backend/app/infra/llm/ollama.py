import logging
from typing import Any

import httpx

from app.domain.ai import AiProvider
from app.infra.llm.base import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMRejectedError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

_FINISH = {"stop": LLMFinish.COMPLETE, "length": LLMFinish.TRUNCATED}


class OllamaProvider:
    """Adaptador de un Ollama propio (A31), solo como IA de la plataforma: lo
    instala y configura quien despliega (`AI_OLLAMA_BASE_URL`), sin clave y sin
    coste por uso. Usa la API nativa: `format` con el esquema, que Ollama impone en
    local con decodificación restringida.

    La dirección sale de la configuración, nunca de un usuario: si cada usuario
    pudiera dar la suya, el servidor haría peticiones a cualquier dirección,
    también de su red interna (SSRF). Por eso no es un proveedor de claves propias.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        context_tokens: int = 16_384,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._context_tokens = context_tokens
        # Solo para las pruebas (un transporte simulado).
        self._http_client = http_client

    @property
    def provider(self) -> AiProvider:
        return AiProvider.OLLAMA

    def _client(self, api_key: str | None) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        # Una clave solo si quien despliega pone Ollama detrás de un proxy con
        # autenticación. Sin seguir redirecciones: no se sale de esa dirección.
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        return httpx.AsyncClient(
            timeout=self._timeout, headers=headers, follow_redirects=False
        )

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str | None
    ) -> LLMResponse:
        # num_ctx: la ventana por defecto de Ollama es pequeña (unos miles de
        # tokens) y, si no cabe, recorta la entrada sin avisar: la propuesta
        # saldría de medio perfil o de media oferta.
        options: dict[str, Any] = {
            "num_ctx": self._context_tokens,
            "num_predict": request.max_output_tokens,
        }
        if request.temperature is not None:
            options["temperature"] = request.temperature
        body = await self._call(
            "POST",
            "/api/chat",
            api_key,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
                "format": dict(request.json_schema),
                "stream": False,
                "options": options,
            },
        )
        message = body.get("message") or {}
        return LLMResponse(
            text=str(message.get("content") or ""),
            input_tokens=int(body.get("prompt_eval_count") or 0),
            output_tokens=int(body.get("eval_count") or 0),
            finish=_FINISH.get(str(body.get("done_reason") or ""), LLMFinish.COMPLETE),
        )

    async def check_access(self, *, model: str, api_key: str | None) -> None:
        # Que el servidor responde y tiene el modelo descargado, sin generar nada.
        body = await self._call("GET", "/api/tags", api_key)
        names = {str(item.get("name")) for item in body.get("models") or []}
        if model not in names and f"{model}:latest" not in names:
            raise LLMRejectedError(status_code=404)

    async def _call(
        self, method: str, path: str, api_key: str | None, **kwargs: Any
    ) -> dict[str, Any]:
        client = self._client(api_key)
        try:
            response = await client.request(method, f"{self._base_url}{path}", **kwargs)
            if response.is_error:
                raise _translate_status(response.status_code)
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Ollama: %s", type(exc).__name__)
            raise LLMUnavailableError() from None
        except ValueError:
            # Una respuesta que no es JSON: no es un Ollama, o está roto.
            logger.warning("Ollama: respuesta que no es JSON")
            raise LLMUnavailableError() from None
        finally:
            if self._http_client is None:
                await client.aclose()
        return data if isinstance(data, dict) else {}


def _translate_status(status: int) -> LLMError:
    """Un código HTTP de Ollama → `LLMError`. Nunca se lee el cuerpo del error."""
    logger.warning("Ollama: HTTP %s", status)
    if status in (401, 403):
        return LLMAuthError(status_code=status)
    if status >= 500:
        return LLMUnavailableError(status_code=status)
    # 404: el modelo no está descargado. 400: no admite lo que se le pide.
    return LLMRejectedError(status_code=status)
