"""Reglas puras de la IA (F15, docs/arquitectura/ia.md)."""

from enum import StrEnum


class AiProvider(StrEnum):
    """Proveedores con adaptador en `infra/llm/` (A31). Quien despliega decide cuáles
    se ofrecen y con qué modelos (decisión 0017); uno nuevo es un adaptador más."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
