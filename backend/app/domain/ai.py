"""Reglas puras de la IA (F15, docs/arquitectura/ia.md).

La pieza central: "no inventar" se garantiza con la forma de la respuesta, no
pidiéndoselo al modelo (ia.md §4). El esquema de la propuesta no tiene campos para
empresas, puestos, fechas ni nombres de habilidades: solo referencias a elementos
del perfil, por ids cortos que se traducen aquí de vuelta a sus UUID (A32).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.cv import (
    CvSection,
    CvSnapshot,
    SnapshotBullet,
    SnapshotEntry,
    SnapshotEntrySection,
)
from app.domain.profile import BULLET_MAX_LENGTH, EntryKind


class AiProvider(StrEnum):
    """Proveedores con adaptador en `infra/llm/` (A31). Quien despliega decide cuáles
    se ofrecen y con qué modelos (decisión 0017); uno nuevo es un adaptador más."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"


class AiTask(StrEnum):
    CV = "cv"
    COVER_LETTER = "cover_letter"


class ProposalStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    # El proveedor respondió, pero la respuesta no pasó la validación (A32).
    INVALID = "invalid"
    # El modelo declaró que la oferta no da para un ajuste útil (RF-119).
    REJECTED = "rejected"
    # El proveedor falló o el trabajo se interrumpió.
    FAILED = "failed"


# Lo que aún puede facturarse: con la clave de la plataforma, cuenta para la cuota
# junto con lo ya facturado (ia.md §6, trampa de las ráfagas).
IN_FLIGHT_STATUSES = (ProposalStatus.QUEUED, ProposalStatus.RUNNING)
# Los que terminan con un código que la interfaz explica.
STATUSES_WITH_ERROR = (
    ProposalStatus.INVALID,
    ProposalStatus.REJECTED,
    ProposalStatus.FAILED,
)


class ProposalLanguage(StrEnum):
    """Idioma en que se escribe la propuesta: los de las etiquetas de los CV."""

    ES = "es"
    EN = "en"


class KeySource(StrEnum):
    """Con qué clave se hizo la llamada. Solo `platform` cuenta para la cuota
    gratuita (RF-152); `user` llega con las claves propias."""

    PLATFORM = "platform"
    USER = "user"


class ProposalErrorCode(StrEnum):
    """Por qué una propuesta no salió. Los `ai_provider_*` y `ai_response_invalid`
    los da el adaptador (`infra/llm/base.py`)."""

    PROVIDER_AUTH = "ai_provider_auth"
    PROVIDER_QUOTA = "ai_provider_quota"
    PROVIDER_UNAVAILABLE = "ai_provider_unavailable"
    PROVIDER_REJECTED = "ai_provider_rejected"
    RESPONSE_INVALID = "ai_response_invalid"
    # El proveedor se negó a responder (filtro de contenido).
    RESPONSE_REFUSED = "ai_response_refused"
    OFFER_INSUFFICIENT = "ai_offer_insufficient"
    # El perfil se quedó sin experiencias entre pedirla y ejecutarla.
    PROFILE_INCOMPLETE = "profile_incomplete"
    # El trabajo se perdió o se quedó colgado y lo cerró el barrido.
    INTERRUPTED = "ai_interrupted"


# Versión del texto del consentimiento (RF-116, ia.md §8). Subirla vuelve a pedir
# consentimiento a todos: se cambia solo si cambia lo que se explica.
AI_CONSENT_VERSION = 1

# Una descripción más corta no da para un ajuste útil (RF-119): se rechaza al
# pedirla, sin gastar el uso. El modelo puede rechazar además una larga que no
# parezca una oferta de empleo, y eso sí lo gasta (decisión 0017).
MIN_JOB_DESCRIPTION_LENGTH = 200

# Versión del prompt de cada tarea (A33): un fichero de `infra/llm/prompts/`. Se
# cambia añadiendo uno nuevo, nunca editando el que ya produjo propuestas.
PROMPT_VERSIONS: dict[AiTask, str] = {AiTask.CV: "cv/v2"}

# Requisitos de la oferta (cv/v2, el encaje con la oferta): lo que pase de aquí se
# recorta en lugar de invalidar la propuesta, porque no cambia lo que dice el CV.
MAX_REQUIREMENTS = 15
MAX_KEYWORDS = 6
REQUIREMENT_MAX_LENGTH = 120
KEYWORD_MAX_LENGTH = 60

# Salida máxima de una propuesta: un CV con muchas experiencias reformuladas, más
# el razonamiento en los modelos que lo cuentan como salida.
MAX_OUTPUT_TOKENS = 16_000

# Barrido de propuestas (como el de documentos, segundo plano §3): una en cola más
# de 2 minutos perdió su trabajo y se reencola; más de una hora, se da por fallida.
QUEUED_REQUEUE_AFTER = timedelta(minutes=2)
QUEUED_GIVE_UP_AFTER = timedelta(hours=1)
# Una en curso más allá del tiempo de espera del proveedor (más margen) se quedó
# colgada: el worker murió a mitad.
RUNNING_GRACE = timedelta(minutes=5)
SWEEP_BATCH = 100


# --- Lo que se envía (ia.md §3) ---------------------------------------------


@dataclass(frozen=True)
class AiEntry:
    id: uuid.UUID
    kind: EntryKind
    title: str
    organization: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str | None
    bullets: Sequence[tuple[uuid.UUID, str]]


@dataclass(frozen=True)
class AiSkill:
    id: uuid.UUID
    name: str
    category: str | None
    level: str | None


@dataclass(frozen=True)
class AiLanguage:
    id: uuid.UUID
    language: str
    level: str


@dataclass(frozen=True)
class AiProfile:
    """Lo que la IA puede ver del perfil. Sin datos de contacto (nombre, email,
    teléfono, ubicación, enlaces): no salen de la aplicación (RNF-06)."""

    headline: str | None
    summary: str | None
    entries: Sequence[AiEntry]
    skills: Sequence[AiSkill]
    # Solo como contexto (carencias y evidencia de un requisito): no se proponen.
    languages: Sequence[AiLanguage]

    @property
    def experiences(self) -> list[AiEntry]:
        return [entry for entry in self.entries if entry.kind == EntryKind.EXPERIENCE]


@dataclass
class ProfileIds:
    """La correspondencia de ids cortos de una petición con los UUID reales.

    Los modelos copian mal los UUID (ia.md §3, trampa): una propuesta válida
    fallaría por un dígito cambiado, y se contaría como uso gastado. `e1`, `e1.b2`
    o `s7` se copian bien y cuestan menos tokens.
    """

    entries: dict[str, uuid.UUID] = field(default_factory=dict)
    # Cada logro, con la experiencia a la que pertenece.
    bullets: dict[str, tuple[str, uuid.UUID]] = field(default_factory=dict)
    skills: dict[str, uuid.UUID] = field(default_factory=dict)
    # Formación, proyectos y certificaciones (`c1`) e idiomas (`l1`): solo pueden
    # citarse como evidencia de un requisito, nunca entran en la propuesta del CV.
    context: dict[str, uuid.UUID] = field(default_factory=dict)
    languages: dict[str, uuid.UUID] = field(default_factory=dict)

    def evidence(self, short_id: str) -> "RequirementEvidence | None":
        """El elemento del perfil al que apunta un id corto citado como evidencia."""
        if short_id in self.entries:
            return RequirementEvidence(kind="entry", id=self.entries[short_id])
        if short_id in self.context:
            return RequirementEvidence(kind="entry", id=self.context[short_id])
        if short_id in self.bullets:
            return RequirementEvidence(kind="bullet", id=self.bullets[short_id][1])
        if short_id in self.skills:
            return RequirementEvidence(kind="skill", id=self.skills[short_id])
        if short_id in self.languages:
            return RequirementEvidence(kind="language", id=self.languages[short_id])
        return None


def _month(value: date | None) -> str:
    return value.strftime("%Y-%m") if value else "?"


def _period(entry: AiEntry) -> str:
    end = "actualidad" if entry.is_current else _month(entry.end_date)
    return f"{_month(entry.start_date)} → {end}"


def build_cv_input(profile: AiProfile) -> tuple[str, ProfileIds]:
    """El perfil como datos para el modelo, con un id corto en cada elemento que la
    propuesta puede referenciar: experiencias, logros y habilidades. El resto
    (formación, proyectos, certificaciones, idiomas) es contexto para las carencias
    (RF-112) y, desde cv/v2, evidencia de un requisito: lleva id (`c1`, `l1`), pero
    la propuesta del CV no puede tocarlo."""
    ids = ProfileIds()
    lines: list[str] = []
    if profile.headline:
        lines.append(f"Titular: {profile.headline}")
    if profile.summary:
        lines.append(f"Resumen actual: {profile.summary}")

    lines.append("\n## Experiencia (referenciable)")
    for index, entry in enumerate(profile.experiences, start=1):
        entry_id = f"e{index}"
        ids.entries[entry_id] = entry.id
        organization = f" — {entry.organization}" if entry.organization else ""
        lines.append(f"[{entry_id}] {entry.title}{organization} ({_period(entry)})")
        if entry.description:
            lines.append(f"    Descripción: {entry.description}")
        for number, (bullet_uuid, text) in enumerate(entry.bullets, start=1):
            bullet_id = f"{entry_id}.b{number}"
            ids.bullets[bullet_id] = (entry_id, bullet_uuid)
            lines.append(f"    [{bullet_id}] {text}")

    lines.append("\n## Habilidades (referenciables)")
    for index, skill in enumerate(profile.skills, start=1):
        skill_id = f"s{index}"
        ids.skills[skill_id] = skill.id
        extra = ", ".join(item for item in (skill.category, skill.level) if item)
        lines.append(f"[{skill_id}] {skill.name}" + (f" ({extra})" if extra else ""))

    context = [entry for entry in profile.entries if entry.kind != EntryKind.EXPERIENCE]
    if context or profile.languages:
        lines.append("\n## Contexto (solo como evidencia de un requisito)")
        for index, entry in enumerate(context, start=1):
            context_id = f"c{index}"
            ids.context[context_id] = entry.id
            organization = f" — {entry.organization}" if entry.organization else ""
            lines.append(
                f"[{context_id}] {entry.kind.value}: {entry.title}{organization} "
                f"({_period(entry)})"
            )
            if entry.description:
                lines.append(f"    Descripción: {entry.description}")
            for _, text in entry.bullets:
                lines.append(f"    - {text}")
        for index, language in enumerate(profile.languages, start=1):
            language_id = f"l{index}"
            ids.languages[language_id] = language.id
            lines.append(
                f"[{language_id}] idioma: {language.language} ({language.level})"
            )

    return "\n".join(lines), ids


def wrap_job_description(text: str) -> str:
    """La oferta delimitada como datos de terceros (RNF-07, ia.md §3). Si el texto
    trajera el delimitador de cierre, se neutraliza para que no pueda "salirse"."""
    safe = text.replace("</oferta>", "</ oferta>")
    return f"<oferta>\n{safe}\n</oferta>"


# --- Lo que vuelve (ia.md §4) -----------------------------------------------


class ProposedBullet(BaseModel):
    bullet_id: str = Field(description="Id corto de un logro del perfil, p. ej. e1.b2")
    text: str = Field(description="Ese logro reformulado para la oferta")


class ProposedExperience(BaseModel):
    entry_id: str = Field(
        description="Id corto de una experiencia del perfil, p. ej. e1"
    )
    bullets: list[ProposedBullet]


class ProposedGap(BaseModel):
    requirement: str = Field(description="Lo que pide la oferta")
    note: str = Field(description="Por qué no aparece en el perfil")


class CvProposalOutputV1(BaseModel):
    """El esquema de cv/v1. Se conserva para poder ejecutar una propuesta pedida
    con esa versión (A33). Las experiencias van en el orden propuesto; las que no
    aparecen quedan fuera del CV."""

    insufficient_offer: bool = Field(
        description="true si el texto no es una oferta de empleo o no da para adaptar"
    )
    summary: str = Field(description="Resumen profesional adaptado a la oferta")
    experiences: list[ProposedExperience]
    skills: list[str] = Field(description="Ids cortos de habilidades, por prioridad")
    gaps: list[ProposedGap] = Field(
        description="Requisitos de la oferta que el perfil no cubre"
    )


class RequirementImportance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class ProposedRequirement(BaseModel):
    requirement: str = Field(description="El requisito, en pocas palabras")
    importance: RequirementImportance = Field(
        description="required si la oferta lo exige; preferred si lo valora"
    )
    keywords: list[str] = Field(
        description="Cómo se buscaría en un CV: como lo dice la oferta, sinónimos, "
        "siglas y variantes"
    )
    evidence: list[str] = Field(
        description="Ids cortos del perfil que lo demuestran; vacío si ninguno"
    )
    note: str = Field(
        description="Sin evidencia: por qué no aparece en el perfil. Con ella, vacío"
    )


class CvProposalOutput(BaseModel):
    """El esquema de cv/v2: el de v1 con los requisitos de la oferta en lugar de las
    carencias sueltas. Los requisitos van primero para que el modelo los tenga
    delante al reformular (los campos se generan en este orden)."""

    insufficient_offer: bool = Field(
        description="true si el texto no es una oferta de empleo o no da para adaptar"
    )
    requirements: list[ProposedRequirement] = Field(
        description="Requisitos de la oferta comprobables en un CV, los más "
        "importantes primero"
    )
    summary: str = Field(description="Resumen profesional adaptado a la oferta")
    experiences: list[ProposedExperience]
    skills: list[str] = Field(description="Ids cortos de habilidades, por prioridad")


# El esquema que corresponde a cada versión del prompt (A33).
CV_OUTPUT_MODELS: dict[str, type[CvProposalOutput] | type[CvProposalOutputV1]] = {
    "cv/v1": CvProposalOutputV1,
    "cv/v2": CvProposalOutput,
}


class ValidatedBullet(BaseModel):
    bullet_id: uuid.UUID
    text: str


class ValidatedExperience(BaseModel):
    entry_id: uuid.UUID
    bullets: list[ValidatedBullet]


class RequirementEvidence(BaseModel):
    """Un elemento del perfil que demuestra un requisito. `entry` es una
    experiencia, formación, proyecto o certificación."""

    kind: Literal["entry", "bullet", "skill", "language"]
    id: uuid.UUID


class Requirement(BaseModel):
    """Un requisito de la oferta. El porcentaje de encaje no lo da la IA: lo
    calcula la interfaz buscando `keywords` en el texto del CV (ia.md §4)."""

    name: str
    importance: RequirementImportance
    keywords: list[str]
    evidence: list[RequirementEvidence]
    note: str


class CvProposal(BaseModel):
    """La propuesta ya validada, con los UUID reales: lo que se guarda y se revisa."""

    summary: str
    experiences: list[ValidatedExperience]
    skill_ids: list[uuid.UUID]
    # Lo que la oferta pide y no está en el perfil (RF-112). Desde cv/v2 sale de
    # los requisitos sin evidencia.
    gaps: list[ProposedGap]
    # Solo desde cv/v2: las propuestas de v1 no tienen encaje con la oferta.
    requirements: list[Requirement] | None = None


class InvalidProposalError(Exception):
    """La respuesta no pasa la validación de referencias (A32, segunda capa). El
    motivo es para el log: no lleva texto del modelo ni del perfil."""


def validate_cv_output(
    output: CvProposalOutput | CvProposalOutputV1, ids: ProfileIds
) -> CvProposal:
    """Segunda capa de A32: cada referencia existe en el perfil de ESTE usuario en
    el momento de la petición. Una sola que no exista invalida toda la propuesta:
    no se corrige ni se descarta en silencio, porque una propuesta con una
    referencia inventada no es de fiar en el resto (ia.md §4)."""
    if not output.summary.strip():
        raise InvalidProposalError("resumen vacío")
    if not output.experiences:
        raise InvalidProposalError("sin experiencias")

    experiences: list[ValidatedExperience] = []
    seen_entries: set[str] = set()
    seen_bullets: set[str] = set()
    for experience in output.experiences:
        if experience.entry_id not in ids.entries:
            raise InvalidProposalError("experiencia inexistente")
        if experience.entry_id in seen_entries:
            raise InvalidProposalError("experiencia repetida")
        seen_entries.add(experience.entry_id)
        bullets: list[ValidatedBullet] = []
        for bullet in experience.bullets:
            owner = ids.bullets.get(bullet.bullet_id)
            if owner is None:
                raise InvalidProposalError("logro inexistente")
            if owner[0] != experience.entry_id:
                raise InvalidProposalError("logro de otra experiencia")
            if bullet.bullet_id in seen_bullets:
                raise InvalidProposalError("logro repetido")
            seen_bullets.add(bullet.bullet_id)
            text = bullet.text.strip()
            if not text or len(text) > BULLET_MAX_LENGTH:
                raise InvalidProposalError("logro vacío o demasiado largo")
            bullets.append(ValidatedBullet(bullet_id=owner[1], text=text))
        experiences.append(
            ValidatedExperience(
                entry_id=ids.entries[experience.entry_id], bullets=bullets
            )
        )

    skill_ids: list[uuid.UUID] = []
    for skill in output.skills:
        if skill not in ids.skills:
            raise InvalidProposalError("habilidad inexistente")
        if ids.skills[skill] in skill_ids:
            raise InvalidProposalError("habilidad repetida")
        skill_ids.append(ids.skills[skill])

    if isinstance(output, CvProposalOutputV1):
        return CvProposal(
            summary=output.summary.strip(),
            experiences=experiences,
            skill_ids=skill_ids,
            gaps=[gap for gap in output.gaps if gap.requirement.strip()],
        )
    requirements = _validate_requirements(output.requirements, ids)
    return CvProposal(
        summary=output.summary.strip(),
        experiences=experiences,
        skill_ids=skill_ids,
        gaps=[
            ProposedGap(requirement=item.name, note=item.note)
            for item in requirements
            if not item.evidence
        ],
        requirements=requirements,
    )


def _validate_requirements(
    proposed: Sequence[ProposedRequirement], ids: ProfileIds
) -> list[Requirement]:
    """La evidencia se valida como cualquier otra referencia: un id que no existe
    invalida la propuesta. Lo demás (cuántos, su longitud) se recorta, porque no
    cambia lo que dice el CV y no merece gastar el uso."""
    requirements: list[Requirement] = []
    for item in proposed:
        evidence: list[RequirementEvidence] = []
        for short_id in item.evidence:
            found = ids.evidence(short_id.strip())
            if found is None:
                raise InvalidProposalError("evidencia inexistente")
            if found not in evidence:
                evidence.append(found)
        name = item.requirement.strip()[:REQUIREMENT_MAX_LENGTH]
        if not name:
            continue
        # El nombre también se busca: así nunca queda un requisito sin palabras.
        keywords: list[str] = []
        for keyword in (*item.keywords, name):
            keyword = keyword.strip()
            if (
                keyword
                and len(keyword) <= KEYWORD_MAX_LENGTH
                and keyword.casefold() not in {k.casefold() for k in keywords}
            ):
                keywords.append(keyword)
        requirements.append(
            Requirement(
                name=name,
                importance=item.importance,
                keywords=keywords[:MAX_KEYWORDS],
                evidence=evidence,
                note="" if evidence else item.note.strip(),
            )
        )
    return requirements[:MAX_REQUIREMENTS]


class OutdatedProposalError(Exception):
    """La propuesta revisada referencia algo que ya no está en el perfil: se editó
    el perfil después de pedirla."""


def apply_cv_proposal(base: CvSnapshot, proposal: CvProposal) -> CvSnapshot:
    """El CV adaptado (RF-110, RF-113): la foto fija del perfil completo con la
    propuesta revisada aplicada.

    De la propuesta salen solo el resumen, qué experiencias y logros van y en qué
    orden, el texto de cada logro y qué habilidades destacar. Puestos, empresas y
    fechas salen de la foto del perfil (RF-111): la propuesta no tiene dónde
    escribirlos. Formación, proyectos, certificaciones e idiomas van como en el
    perfil."""
    experience = next(
        (s for s in base.entry_sections if s.section == CvSection.EXPERIENCE), None
    )
    entries = {entry.id: entry for entry in experience.entries} if experience else {}
    adapted: list[SnapshotEntry] = []
    for proposed in proposal.experiences:
        entry = entries.get(proposed.entry_id)
        if entry is None:
            raise OutdatedProposalError("experiencia que ya no está en el perfil")
        bullets = {bullet.id for bullet in entry.bullets}
        if any(bullet.bullet_id not in bullets for bullet in proposed.bullets):
            raise OutdatedProposalError("logro que ya no está en esa experiencia")
        adapted.append(
            entry.model_copy(
                update={
                    "bullets": [
                        SnapshotBullet(id=bullet.bullet_id, text=bullet.text)
                        for bullet in proposed.bullets
                    ]
                }
            )
        )

    skills = {skill.id: skill for skill in base.skills}
    if any(skill_id not in skills for skill_id in proposal.skill_ids):
        raise OutdatedProposalError("habilidad que ya no está en el perfil")

    sections = [
        SnapshotEntrySection(section=CvSection.EXPERIENCE, entries=adapted)
        if section.section == CvSection.EXPERIENCE
        else section
        for section in base.entry_sections
    ]
    return base.model_copy(
        update={
            "summary": proposal.summary,
            "entry_sections": [section for section in sections if section.entries],
            "skills": [skills[skill_id] for skill_id in proposal.skill_ids],
        }
    )


def cost_micros(
    input_tokens: int,
    output_tokens: int,
    input_usd_per_mtok: float,
    output_usd_per_mtok: float,
) -> int:
    """Coste estimado en millonésimas de dólar: un precio por millón de tokens por
    los tokens da justo eso. Solo informativo (no hay tope global, 0017)."""
    return round(
        input_tokens * input_usd_per_mtok + output_tokens * output_usd_per_mtok
    )
