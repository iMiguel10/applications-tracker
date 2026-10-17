"""Una llamada a la IA sin base de datos: preparar la petición y entender la
respuesta. La usan `AiProposalService` (el worker) y la evaluación manual
(`evals/ai/`, RNF-23), para que lo que se evalúa sea exactamente lo que se ejecuta.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.domain.ai import (
    MAX_OUTPUT_TOKENS,
    OUTPUT_MODELS,
    REASONING,
    TEMPERATURE,
    AiProfile,
    AiTask,
    CoverLetterOutput,
    CoverLetterProposal,
    CvProposal,
    InvalidProposalError,
    ProfileIds,
    ProposalErrorCode,
    ProposalStatus,
    build_cv_input,
    describe_application,
    validate_cv_output,
    validate_letter_output,
    wrap_job_description,
)
from app.infra.llm import LLMFinish, LLMRequest, LLMResponse, strict_json_schema
from app.infra.llm.prompts import load_prompt


@dataclass(frozen=True)
class PreparedCall:
    request: LLMRequest
    # Los ids cortos que se enviaron: la respuesta se valida contra ellos.
    ids: ProfileIds
    output_model: type[BaseModel]


def prepare_call(
    profile: AiProfile,
    *,
    kind: AiTask,
    prompt_version: str,
    language: str,
    job_description: str,
    position_title: str,
    company_name: str,
) -> PreparedCall:
    """La petición de una propuesta: el prompt de su versión, el perfil con ids
    cortos y la oferta delimitada (y, en la carta, el puesto y la empresa)."""
    profile_text, ids = build_cv_input(profile)
    letter = kind == AiTask.COVER_LETTER
    # El esquema de la versión con que se pidió (A33): una propuesta en cola al
    # cambiar de versión se ejecuta con el prompt y el esquema de la suya.
    output_model = OUTPUT_MODELS[prompt_version]
    offer = wrap_job_description(job_description)
    if letter:
        # La carta va a un puesto y una empresa concretos.
        offer = f"{describe_application(position_title, company_name)}\n\n{offer}"
    request = LLMRequest(
        system=load_prompt(prompt_version, language=language),
        user=f"{profile_text}\n\n{offer}",
        schema_name="cover_letter" if letter else "cv_proposal",
        json_schema=strict_json_schema(output_model),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=TEMPERATURE,
        reasoning=REASONING[kind],
    )
    return PreparedCall(request=request, ids=ids, output_model=output_model)


@dataclass(frozen=True)
class Interpretation:
    """Qué dijo el proveedor, una vez validado. `reason` explica un `invalid` sin
    texto del modelo ni del perfil: va a los logs y al informe de la evaluación."""

    status: ProposalStatus
    error_code: ProposalErrorCode | None = None
    proposal: CvProposal | CoverLetterProposal | None = None
    reason: str | None = None


def interpret_response(response: LLMResponse, call: PreparedCall) -> Interpretation:
    """La respuesta del proveedor, validada contra el perfil enviado (RF-111): una
    referencia inventada, un esquema roto o una respuesta cortada la invalidan."""
    if response.finish == LLMFinish.REFUSED:
        return Interpretation(
            ProposalStatus.INVALID, ProposalErrorCode.RESPONSE_REFUSED, reason="refused"
        )
    if response.finish == LLMFinish.TRUNCATED:
        return Interpretation(
            ProposalStatus.INVALID,
            ProposalErrorCode.RESPONSE_INVALID,
            reason="cortada por longitud",
        )
    try:
        output = call.output_model.model_validate_json(response.text)
    except ValidationError:
        return Interpretation(
            ProposalStatus.INVALID,
            ProposalErrorCode.RESPONSE_INVALID,
            reason="no cumple el esquema",
        )
    if getattr(output, "insufficient_offer", False):
        return Interpretation(
            ProposalStatus.REJECTED, ProposalErrorCode.OFFER_INSUFFICIENT
        )
    try:
        validated = (
            validate_letter_output(output, call.ids)
            if isinstance(output, CoverLetterOutput)
            else validate_cv_output(output, call.ids)  # type: ignore[arg-type]
        )
    except InvalidProposalError as exc:
        return Interpretation(
            ProposalStatus.INVALID, ProposalErrorCode.RESPONSE_INVALID, reason=str(exc)
        )
    return Interpretation(ProposalStatus.SUCCEEDED, proposal=validated)
