"""Comprueba el proveedor de IA de la plataforma con una llamada real (F15).

    docker compose exec api python -m app.scripts.check_ai_provider

Primero valida la clave y el modelo sin generar nada; después pide una respuesta
mínima con salida estructurada estricta, la misma vía que usan las propuestas, y
muestra los tokens que costó (unas decenas). Sirve para comprobar
AI_PLATFORM_PROVIDER, AI_PLATFORM_MODEL y AI_PLATFORM_API_KEY al desplegar o al
cambiar de modelo. Termina con código 0 si todo funciona y con 1 si no.
"""

import argparse
import asyncio
import sys

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.infra.llm import (
    LLMError,
    LLMRequest,
    build_llm_providers,
    platform_model,
    strict_json_schema,
)


class Ping(BaseModel):
    ok: bool
    language: str


async def main() -> int:
    platform = platform_model(settings)
    if platform is None:
        print("Sin IA de plataforma: define AI_PLATFORM_PROVIDER.", file=sys.stderr)
        return 1
    adapter = build_llm_providers(settings).get(platform.provider)
    if adapter is None:
        print(f"Sin adaptador para {platform.provider}.", file=sys.stderr)
        return 1

    label = f"{platform.provider}/{platform.model}"
    try:
        await adapter.check_access(model=platform.model, api_key=platform.api_key)
        response = await adapter.complete(
            LLMRequest(
                system="Responde solo con el JSON pedido.",
                user='Devuelve ok = true y language = "es".',
                schema_name="ping",
                json_schema=strict_json_schema(Ping),
                max_output_tokens=500,
            ),
            model=platform.model,
            api_key=platform.api_key,
        )
    except LLMError as exc:
        print(f"{label}: falló con {exc.code}.", file=sys.stderr)
        return 1

    try:
        Ping.model_validate_json(response.text)
    except ValidationError:
        print(f"{label}: la respuesta no cumple el esquema.", file=sys.stderr)
        return 1

    print(
        f"{label}: funciona ({response.finish}, {response.input_tokens} tokens "
        f"de entrada y {response.output_tokens} de salida)."
    )
    return 0


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    sys.exit(asyncio.run(main()))
