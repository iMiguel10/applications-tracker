"""Evaluación manual de la IA (RNF-23, ia.md §9). Fuera de la CI: llama de verdad
a los proveedores, y con uno de pago, cuesta.

Pasa los casos de `cases/` por cada modelo y tarea, con el mismo prompt, la misma
entrada y la misma validación que la aplicación (`services/ai_call.py`), y cuenta
cuántas propuestas salen válidas y por qué fallan las demás. Escribe una tabla y
un informe en `results/` (fuera de git) con todos los textos, para leerlos a ojo.

    docker compose exec api python -m evals.ai.run --target ollama:qwen3:8b --runs 2
    docker compose exec -e EVAL_ANTHROPIC_API_KEY=… api python -m evals.ai.run \\
        --target anthropic:claude-sonnet-5-5 --task cover_letter --yes

La clave de la plataforma sale de la configuración; la de otro proveedor, de
`EVAL_<PROVEEDOR>_API_KEY`, solo en esa ejecución. Nunca se guarda ni se imprime.
"""

import argparse
import asyncio
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, settings
from app.domain.ai import PROMPT_VERSIONS, AiProvider, AiTask, ProposalStatus
from app.infra.llm import (
    LLMError,
    LLMInvalidOutputError,
    LLMProvider,
    build_llm_providers,
)
from app.services.ai_call import interpret_response, prepare_call
from evals.ai.cases import EvalCase, load_cases
from evals.ai.checks import Checks, check_proposal, proposal_texts

RESULTS_DIR = Path(__file__).parent / "results"
# Sin coste por uso: no hace falta confirmar.
FREE_PROVIDERS = {AiProvider.OLLAMA}


@dataclass(frozen=True)
class Target:
    provider: AiProvider
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider.value}:{self.model}"


def parse_target(value: str) -> Target:
    provider, _, model = value.partition(":")
    if not model:
        raise argparse.ArgumentTypeError(f"{value!r}: usa proveedor:modelo")
    try:
        return Target(AiProvider(provider), model)
    except ValueError:
        options = ", ".join(item.value for item in AiProvider)
        raise argparse.ArgumentTypeError(
            f"{provider!r} no es un proveedor ({options})"
        ) from None


def api_key_for(
    target: Target, config: Settings, environ: Mapping[str, str]
) -> str | None:
    """La clave con que se llama: la de la plataforma si es su proveedor; si no, la
    de `EVAL_<PROVEEDOR>_API_KEY`. Ollama no necesita ninguna."""
    if config.ai_platform_provider == target.provider and config.ai_platform_api_key:
        return config.ai_platform_api_key
    if target.provider == AiProvider.OLLAMA:
        return None
    key = environ.get(f"EVAL_{target.provider.value.upper()}_API_KEY")
    if not key:
        raise SystemExit(
            f"Falta la clave de {target.provider.value}: pásala con "
            f"-e EVAL_{target.provider.value.upper()}_API_KEY=…"
        )
    return key


@dataclass
class RunResult:
    case: str
    target: str
    task: AiTask
    run: int
    status: str
    error_code: str | None
    reason: str | None
    seconds: float
    input_tokens: int
    output_tokens: int
    # Si salió lo que el caso espera: una propuesta, o el rechazo de RF-119.
    expected: bool
    checks: Checks | None = None
    texts: list[str] = field(default_factory=list)


async def run_one(
    adapter: LLMProvider,
    target: Target,
    api_key: str | None,
    case: EvalCase,
    task: AiTask,
    run: int,
) -> RunResult:
    call = prepare_call(
        case.profile,
        kind=task,
        prompt_version=PROMPT_VERSIONS[task],
        language=case.language,
        job_description=case.job_description,
        position_title=case.position_title,
        company_name=case.company,
    )
    started = time.monotonic()
    try:
        response = await adapter.complete(
            call.request, model=target.model, api_key=api_key
        )
    except LLMError as exc:
        status = (
            ProposalStatus.INVALID
            if isinstance(exc, LLMInvalidOutputError)
            else ProposalStatus.FAILED
        )
        return RunResult(
            case=case.name,
            target=target.label,
            task=task,
            run=run,
            status=status.value,
            error_code=exc.code,
            reason=None,
            seconds=time.monotonic() - started,
            input_tokens=0,
            output_tokens=0,
            expected=False,
        )
    seconds = time.monotonic() - started
    result = interpret_response(response, call)
    wanted = (
        ProposalStatus.SUCCEEDED
        if case.expect == "proposal"
        else ProposalStatus.REJECTED
    )
    run_result = RunResult(
        case=case.name,
        target=target.label,
        task=task,
        run=run,
        status=result.status.value,
        error_code=result.error_code.value if result.error_code else None,
        reason=result.reason,
        seconds=seconds,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        expected=result.status == wanted,
    )
    if result.proposal is not None:
        run_result.checks = check_proposal(
            result.proposal,
            case.profile,
            raw=response.text,
            job_description=case.job_description,
            irrelevant=case.irrelevant,
        )
        run_result.texts = proposal_texts(result.proposal)
    return run_result


@dataclass
class Summary:
    target: str
    task: AiTask
    runs: int = 0
    expected: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    seconds: float = 0
    output_tokens: int = 0
    # Propuestas válidas sin ninguna pista de las comprobaciones automáticas.
    clean: int = 0
    succeeded: int = 0


def summarize(results: Sequence[RunResult]) -> list[Summary]:
    summaries: dict[tuple[str, AiTask], Summary] = {}
    for result in results:
        item = summaries.setdefault(
            (result.target, result.task), Summary(result.target, result.task)
        )
        item.runs += 1
        item.expected += result.expected
        item.by_status[result.status] = item.by_status.get(result.status, 0) + 1
        item.seconds += result.seconds
        item.output_tokens += result.output_tokens
        if result.checks is not None:
            item.succeeded += 1
            item.clean += result.checks.clean
    return list(summaries.values())


def format_table(summaries: Sequence[Summary]) -> str:
    header = (
        "| Modelo | Tarea | Como se esperaba | Estados | Sin pistas | "
        "Tiempo medio | Tokens de salida (media) |"
    )
    lines = [header, "|---|---|---|---|---|---|---|"]
    for item in summaries:
        statuses = ", ".join(f"{k} {v}" for k, v in sorted(item.by_status.items()))
        lines.append(
            f"| {item.target} | {item.task.value} | {item.expected}/{item.runs} | "
            f"{statuses} | {item.clean}/{item.succeeded} | "
            f"{item.seconds / item.runs:.0f} s | {item.output_tokens // item.runs} |"
        )
    return "\n".join(lines)


def format_report(results: Sequence[RunResult], started: datetime) -> str:
    """El informe completo: la tabla y, por cada llamada, el resultado, las pistas
    de las comprobaciones y los textos propuestos, para revisarlos a ojo."""
    lines = [
        f"# Evaluación de la IA, {started:%Y-%m-%d %H:%M} UTC",
        "",
        format_table(summarize(results)),
        "",
        (
            "«Sin pistas»: propuestas válidas en las que las comprobaciones "
            "automáticas no encontraron ids en el texto, cifras cambiadas o nuevas, "
            "ni lo que no viene al caso. No sustituye a leerlas."
        ),
    ]
    for result in results:
        lines += [
            "",
            f"## {result.case} · {result.task.value} · {result.target} · vuelta {result.run}",
            "",
            f"- Estado: **{result.status}**"
            + (f" (`{result.error_code}`)" if result.error_code else "")
            + (" — como se esperaba" if result.expected else " — **no esperado**"),
            (
                f"- {result.seconds:.0f} s, {result.input_tokens} tokens de entrada y "
                f"{result.output_tokens} de salida"
            ),
        ]
        if result.reason:
            lines.append(f"- Motivo: {result.reason}")
        if result.checks is not None:
            checks = result.checks
            lines.append(f"- Ids en el texto: {checks.ids_in_text}")
            for label, values in (
                ("Cifras perdidas al reescribir", checks.changed_figures),
                (
                    "Cifras que no están en el perfil ni en la oferta",
                    checks.new_numbers,
                ),
                ("Lo que no viene al caso", checks.irrelevant),
            ):
                if values:
                    lines.append(f"- {label}: {'; '.join(values)}")
        if result.texts:
            lines += ["", *[f"> {text}\n>" for text in result.texts]]
    return "\n".join(lines) + "\n"


async def evaluate(
    targets: Sequence[Target],
    tasks: Sequence[AiTask],
    cases: Sequence[EvalCase],
    runs: int,
    config: Settings,
    environ: Mapping[str, str],
    providers: Mapping[AiProvider, LLMProvider] | None = None,
) -> list[RunResult]:
    adapters = providers if providers is not None else build_llm_providers(config)
    keys = {target: api_key_for(target, config, environ) for target in targets}
    results: list[RunResult] = []
    total = len(targets) * len(tasks) * len(cases) * runs
    for target in targets:
        adapter = adapters.get(target.provider)
        if adapter is None:
            raise SystemExit(
                f"{target.provider.value} no está disponible en esta configuración"
            )
        for task in tasks:
            for case in cases:
                for run in range(1, runs + 1):
                    result = await run_one(
                        adapter, target, keys[target], case, task, run
                    )
                    results.append(result)
                    print(
                        f"[{len(results)}/{total}] {target.label} {task.value} "
                        f"{case.name} #{run}: {result.status}"
                        + (f" ({result.error_code})" if result.error_code else "")
                        + f", {result.seconds:.0f} s",
                        flush=True,
                    )
    return results


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--target",
        action="append",
        type=parse_target,
        help="proveedor:modelo; se puede repetir. Por defecto, la IA de la plataforma",
    )
    parser.add_argument(
        "--task",
        default="cv,cover_letter",
        help="cv, cover_letter o las dos separadas por comas",
    )
    parser.add_argument("--runs", type=int, default=1, help="vueltas por caso")
    parser.add_argument(
        "--case", action="append", help="solo este caso (nombre del .json); se repite"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirmar las llamadas a proveedores de pago",
    )
    args = parser.parse_args(argv)

    targets: list[Target] = args.target or []
    if not targets:
        if settings.ai_platform_provider is None or not settings.ai_platform_model:
            raise SystemExit(
                "Sin IA de la plataforma: indica --target proveedor:modelo"
            )
        targets = [Target(settings.ai_platform_provider, settings.ai_platform_model)]
    tasks = [AiTask(value.strip()) for value in args.task.split(",") if value.strip()]
    cases = load_cases(set(args.case) if args.case else None)
    if not cases:
        raise SystemExit("No hay casos con ese nombre")

    calls = len(targets) * len(tasks) * len(cases) * args.runs
    paid = [t.label for t in targets if t.provider not in FREE_PROVIDERS]
    print(
        f"{calls} llamadas: {len(cases)} casos × {len(tasks)} tareas × {args.runs} vueltas"
    )
    if paid and not args.yes:
        raise SystemExit(
            f"{', '.join(paid)} cobra cada llamada. Repite con --yes para confirmarlo."
        )

    started = datetime.now(UTC)
    results = asyncio.run(
        evaluate(targets, tasks, cases, args.runs, settings, os.environ)
    )
    RESULTS_DIR.mkdir(exist_ok=True)
    report = RESULTS_DIR / f"{started:%Y%m%d-%H%M%S}.md"
    report.write_text(format_report(results, started), encoding="utf-8")
    print()
    print(format_table(summarize(results)))
    print(f"\nInforme con los textos: {report.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
