"""Prompts versionados (A33): `<tarea>/v<N>.md`. Cambiar un prompt es añadir un
fichero nuevo y apuntar la tarea a él (`PROMPT_VERSIONS` de domain/ai.py), nunca
editar uno que ya produjo propuestas: cada propuesta guarda con qué versión se
hizo y debe poder explicarse con ella (RF-115)."""

from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

LANGUAGE_NAMES = {"es": "español", "en": "inglés"}


@cache
def _read(version: str) -> str:
    path = (PROMPTS_DIR / f"{version}.md").resolve()
    # La versión viene del código, pero que nunca lea fuera de esta carpeta.
    if PROMPTS_DIR.resolve() not in path.parents:
        raise ValueError(f"versión de prompt no válida: {version}")
    return path.read_text(encoding="utf-8")


def load_prompt(version: str, *, language: str) -> str:
    """El prompt `version` con el idioma en que se escribe la propuesta."""
    return _read(version).replace("{{language}}", LANGUAGE_NAMES[language])
