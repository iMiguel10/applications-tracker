"""La evaluación manual de la IA (`evals/ai/`, RNF-23) sin llamar a nadie: que
cargue los casos, clasifique cada respuesta como la aplicación y que sus
comprobaciones encuentren lo que la validación no ve."""

import json
from typing import Any

import pytest

from app.core.config import Settings, settings
from app.domain.ai import AiProvider, AiTask
from app.infra.llm import LLMUnavailableError
from app.infra.llm.fake import FakeLLMProvider
from evals.ai.cases import load_cases
from evals.ai.checks import count_ids_in_text, numbers
from evals.ai.run import (
    Target,
    api_key_for,
    evaluate,
    format_table,
    main,
    run_one,
    summarize,
)

GROQ = Target(AiProvider.GROQ, "openai/gpt-oss-120b")


def cv_output(**changes: Any) -> str:
    """Una respuesta válida para backend-es, con los defectos que debe detectar:
    un id en el texto, una cifra perdida, otra cambiada y lo que no viene al caso."""
    values: dict[str, Any] = {
        "insufficient_offer": False,
        "requirements": [
            {
                "requirement": "PostgreSQL",
                "importance": "required",
                "keywords": ["PostgreSQL"],
                "evidence": ["s2", "e1.b2"],
                "note": "",
            }
        ],
        "summary": "Backend con FastAPI y PostgreSQL [e1.b1]",
        "experiences": [
            {
                "entry_id": "e1",
                "bullets": [
                    {
                        "bullet_id": "e1.b1",
                        "text": "Diseñé servicios web con FastAPI para 75 clientes",
                    },
                    {
                        "bullet_id": "e1.b2",
                        "text": "Optimicé consultas en PostgreSQL y reduje el tiempo de respuesta",
                    },
                    {
                        "bullet_id": "e1.b4",
                        "text": "Organicé las cenas de Navidad del equipo",
                    },
                ],
            }
        ],
        "skills": ["s1", "s2"],
    } | changes
    return json.dumps(values)


def config(**changes: Any) -> Settings:
    return Settings(**(settings.model_dump() | changes))


def test_the_cases_load_as_profiles_with_their_expectations():
    cases = {case.name: case for case in load_cases()}

    assert set(cases) == {
        "backend-es",
        "frontend-en",
        "career-change-es",
        "not-an-offer-es",
    }
    assert cases["not-an-offer-es"].expect == "rejected"
    assert cases["backend-es"].irrelevant == ("Navidad",)
    assert cases["backend-es"].profile.experiences
    # Cada carga, ids nuevos: nada del caso depende de un UUID fijo.
    assert load_cases({"backend-es"})[0].profile.entries[0].id != (
        cases["backend-es"].profile.entries[0].id
    )


@pytest.mark.asyncio
async def test_a_valid_cv_is_scored_with_the_hints_the_validation_cannot_see():
    [case] = load_cases({"backend-es"})
    fake = FakeLLMProvider()
    fake.reply(cv_output())

    result = await run_one(fake, GROQ, "clave", case, AiTask.CV, 1)

    assert result.status == "succeeded"
    assert result.expected is True
    assert result.checks is not None
    assert result.checks.ids_in_text == 1
    assert len(result.checks.changed_figures) == 2
    assert result.checks.new_numbers == ["75"]
    assert result.checks.irrelevant == ["Navidad"]
    assert result.checks.clean is False
    # Los textos son los ya validados: sin el id que se coló.
    assert all("[e1.b1]" not in text for text in result.texts)
    # La misma petición que la aplicación: prompt, esquema y oferta delimitada.
    [call] = fake.calls
    assert call.request.schema_name == "cv_proposal"
    assert "<oferta>" in call.request.user
    assert call.api_key == "clave"


@pytest.mark.asyncio
async def test_rejecting_what_is_not_an_offer_is_the_expected_result():
    [case] = load_cases({"not-an-offer-es"})
    fake = FakeLLMProvider()
    fake.reply(cv_output(insufficient_offer=True))

    result = await run_one(fake, GROQ, None, case, AiTask.CV, 1)

    assert (result.status, result.error_code, result.expected) == (
        "rejected",
        "ai_offer_insufficient",
        True,
    )


@pytest.mark.asyncio
async def test_invented_references_and_provider_errors_are_counted_with_their_reason():
    [case] = load_cases({"backend-es"})
    fake = FakeLLMProvider()
    fake.reply(cv_output(skills=["s99"]))
    fake.fail(LLMUnavailableError())

    invalid = await run_one(fake, GROQ, None, case, AiTask.CV, 1)
    failed = await run_one(fake, GROQ, None, case, AiTask.CV, 2)

    assert (invalid.status, invalid.error_code, invalid.expected) == (
        "invalid",
        "ai_response_invalid",
        False,
    )
    assert invalid.reason == "habilidad inexistente"
    assert (failed.status, failed.error_code) == ("failed", "ai_provider_unavailable")


@pytest.mark.asyncio
async def test_the_summary_counts_each_model_and_task():
    cases = load_cases({"backend-es", "not-an-offer-es"})
    fake = FakeLLMProvider()
    fake.reply(cv_output())
    fake.reply(cv_output(insufficient_offer=True))

    results = await evaluate(
        [GROQ],
        [AiTask.CV],
        cases,
        1,
        config(),
        {"EVAL_GROQ_API_KEY": "gsk_eval"},
        providers={AiProvider.GROQ: fake},
    )
    [summary] = summarize(results)

    assert (summary.runs, summary.expected, summary.succeeded, summary.clean) == (
        2,
        2,
        1,
        0,
    )
    assert summary.by_status == {"rejected": 1, "succeeded": 1}
    assert "| groq:openai/gpt-oss-120b | cv | 2/2 |" in format_table([summary])


def test_the_key_comes_from_the_platform_or_from_the_environment_never_from_a_file():
    platform = config(
        ai_platform_provider="groq",
        ai_platform_model="openai/gpt-oss-120b",
        ai_platform_api_key="gsk_platform",
    )
    anthropic = Target(AiProvider.ANTHROPIC, "claude-sonnet-5-5")
    ollama = Target(AiProvider.OLLAMA, "qwen3:8b")

    assert api_key_for(GROQ, platform, {}) == "gsk_platform"
    assert (
        api_key_for(anthropic, platform, {"EVAL_ANTHROPIC_API_KEY": "sk-ant"})
        == "sk-ant"
    )
    assert api_key_for(ollama, config(ai_platform_provider=None), {}) is None
    with pytest.raises(SystemExit, match="EVAL_ANTHROPIC_API_KEY"):
        api_key_for(anthropic, platform, {})


def test_a_paid_provider_needs_an_explicit_yes_before_any_call():
    with pytest.raises(SystemExit, match="--yes"):
        main(["--target", "groq:openai/gpt-oss-120b", "--case", "backend-es"])


def test_numbers_and_short_ids_are_found_where_they_matter():
    assert numbers("reduje un 40 % en 1,5 años") == {"40", "1.5"}
    raw = json.dumps({"summary": "Con FastAPI (e1.b2) y s3", "skills": ["s1"]})
    # En los campos de referencias (skills) son correctos; en el texto, no.
    assert count_ids_in_text(raw) == 2
    assert count_ids_in_text("no es json") == 0
