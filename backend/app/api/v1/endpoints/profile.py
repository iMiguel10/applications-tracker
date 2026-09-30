import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import (
    get_current_user,
    get_profile_entry_service,
    get_profile_service,
    get_profile_skill_service,
)
from app.schemas.common import error_responses
from app.schemas.profile import (
    EntryCreate,
    EntryOrder,
    EntryRead,
    EntryUpdate,
    LanguageRead,
    LanguagesUpdate,
    ProfileRead,
    ProfileUpdate,
    SkillRead,
    SkillsUpdate,
)
from app.schemas.user import CurrentUser
from app.services.profile_entry_service import ProfileEntryService
from app.services.profile_service import ProfileService
from app.services.profile_skill_service import ProfileSkillService

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


@router.get("", summary="Perfil profesional del usuario actual")
async def read_profile(
    current_user: CurrentUser = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    """Datos de contacto y resumen del CV (RF-100). Un perfil que nunca se ha
    guardado se devuelve vacío, no como 404."""
    return await profiles.get(current_user.id)


@router.put(
    "",
    summary="Guarda el perfil profesional del usuario actual",
    responses=error_responses(422),
)
async def update_profile(
    data: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    """Sustituye los datos básicos enteros: un campo que no se envía queda vacío.
    Los enlaces solo admiten `http` y `https` (hasta 10)."""
    return await profiles.update(current_user.id, data)


# --- Entradas: experiencia, formación, proyectos y certificaciones -------------


@router.get("/entries", summary="Entradas del perfil")
async def list_entries(
    current_user: CurrentUser = Depends(get_current_user),
    entries: ProfileEntryService = Depends(get_profile_entry_service),
) -> list[EntryRead]:
    """Experiencia, formación, proyectos y certificaciones (RF-101, RF-102), cada
    una con sus logros, ordenadas por sección (`kind`) y por su posición."""
    return [
        EntryRead.model_validate(entry) for entry in await entries.list(current_user.id)
    ]


@router.post(
    "/entries",
    status_code=status.HTTP_201_CREATED,
    summary="Añade una entrada al perfil",
    responses=error_responses(409, 422),
)
async def create_entry(
    data: EntryCreate,
    current_user: CurrentUser = Depends(get_current_user),
    entries: ProfileEntryService = Depends(get_profile_entry_service),
) -> EntryRead:
    """La entrada se añade al final de su sección. Cada sección tiene un tope (50
    experiencias; 30 formaciones, proyectos o certificaciones): al alcanzarlo
    responde **409** `profile_section_full` con `limit` y `used`. Hasta 20 logros
    por entrada."""
    return EntryRead.model_validate(await entries.create(current_user.id, data))


# Antes que /entries/{entry_id}: si no, "order" se leería como un id.
@router.put(
    "/entries/order",
    summary="Reordena una sección del perfil",
    responses=error_responses(422),
)
async def reorder_entries(
    data: EntryOrder,
    current_user: CurrentUser = Depends(get_current_user),
    entries: ProfileEntryService = Depends(get_profile_entry_service),
) -> list[EntryRead]:
    """`entry_ids` trae **todos** los ids de la sección, en el orden nuevo. Uno de
    más, uno de menos o uno repetido responde **422** `entry_order_mismatch`.
    Devuelve todas las entradas, como el listado."""
    reordered = await entries.reorder(current_user.id, data)
    return [EntryRead.model_validate(entry) for entry in reordered]


@router.put(
    "/entries/{entry_id}",
    summary="Guarda una entrada del perfil",
    responses=error_responses(404, 422),
)
async def update_entry(
    entry_id: uuid.UUID,
    data: EntryUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    entries: ProfileEntryService = Depends(get_profile_entry_service),
) -> EntryRead:
    """Sustituye la entrada entera; la sección no cambia. En `bullets`, un logro con
    `id` edita el existente y conserva su id; uno sin `id` es nuevo; los que no
    vienen se borran. Un `id` que no es de esta entrada responde **422**
    `bullet_not_in_entry`."""
    return EntryRead.model_validate(
        await entries.update(current_user.id, entry_id, data)
    )


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borra una entrada del perfil",
    responses=error_responses(404),
)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    entries: ProfileEntryService = Depends(get_profile_entry_service),
) -> None:
    """Borra la entrada con sus logros. Los CVs ya generados no cambian: guardan
    una copia de lo que se usó."""
    await entries.delete(current_user.id, entry_id)


# --- Habilidades e idiomas ------------------------------------------------------


@router.get("/skills", summary="Habilidades del perfil")
async def list_skills(
    current_user: CurrentUser = Depends(get_current_user),
    skills: ProfileSkillService = Depends(get_profile_skill_service),
) -> list[SkillRead]:
    """Las habilidades (RF-102), en su orden."""
    return [
        SkillRead.model_validate(skill)
        for skill in await skills.skills(current_user.id)
    ]


@router.put(
    "/skills",
    summary="Guarda las habilidades del perfil",
    responses=error_responses(422),
)
async def replace_skills(
    data: SkillsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    skills: ProfileSkillService = Depends(get_profile_skill_service),
) -> list[SkillRead]:
    """Sustituye la lista entera (hasta 100), en el orden en que se envía. Una
    habilidad con `id` edita la existente y conserva su id; una sin `id` es nueva;
    las que no vienen se borran. Un nombre repetido (sin distinguir mayúsculas)
    responde **422** `duplicate_skill`, y un `id` que no es de este perfil, **422**
    `skill_not_in_profile`."""
    replaced = await skills.replace_skills(current_user.id, data)
    return [SkillRead.model_validate(skill) for skill in replaced]


@router.get("/languages", summary="Idiomas del perfil")
async def list_languages(
    current_user: CurrentUser = Depends(get_current_user),
    skills: ProfileSkillService = Depends(get_profile_skill_service),
) -> list[LanguageRead]:
    """Los idiomas con su nivel (MCER o nativo), en su orden."""
    return [
        LanguageRead.model_validate(language)
        for language in await skills.languages(current_user.id)
    ]


@router.put(
    "/languages",
    summary="Guarda los idiomas del perfil",
    responses=error_responses(422),
)
async def replace_languages(
    data: LanguagesUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    skills: ProfileSkillService = Depends(get_profile_skill_service),
) -> list[LanguageRead]:
    """Sustituye la lista entera (hasta 30), igual que las habilidades. Un idioma
    repetido responde **422** `duplicate_language`, y un `id` que no es de este
    perfil, **422** `language_not_in_profile`."""
    replaced = await skills.replace_languages(current_user.id, data)
    return [LanguageRead.model_validate(language) for language in replaced]
