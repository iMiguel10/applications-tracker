import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.domain.cv import CvSection
from app.domain.documents import TEMPLATE_MAX_LENGTH
from app.schemas.common import OptionalShortText

# Tope de elementos excluidos: más que todo lo que cabe en un perfil (§10).
MAX_EXCLUDED_IDS = 2000


class CvDesignRead(BaseModel):
    """Un diseño de CV (RF-104): una carpeta de plantillas, sin código propio."""

    key: str = Field(examples=["modern"])
    names: dict[str, str] = Field(
        description="Nombre visible por idioma de la interfaz.",
        examples=[{"es": "Moderno", "en": "Modern"}],
    )
    descriptions: dict[str, str] = Field(
        description="Descripción breve por idioma de la interfaz."
    )
    languages: list[str] = Field(
        description="Idiomas en que puede salir el CV (sus etiquetas fijas).",
        examples=[["es", "en"]],
    )
    ats_friendly: bool = Field(
        description="RF-105: `false` en un diseño gráfico que un ATS podría leer "
        "desordenado. La interfaz lo avisa antes de generar."
    )


class CvGenerateRequest(BaseModel):
    """Qué CV generar desde el perfil (RF-103). Se guarda tal cual era el perfil al
    pedirlo (foto fija, A27): editarlo después no cambia el CV."""

    design: Annotated[
        str, StringConstraints(min_length=1, max_length=TEMPLATE_MAX_LENGTH)
    ] = Field(description="Clave del diseño (`GET /documents/cv-designs`).")
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] = Field(
        description='Idioma de las etiquetas fijas ("Experiencia" / '
        '"Experience"). El contenido sale como está escrito en el perfil (RF-106).',
        examples=["es"],
    )
    name: OptionalShortText = Field(
        default=None,
        description="Nombre visible en la biblioteca. Sin él, `CV <diseño>`.",
        examples=["CV backend – Moderno"],
    )
    sections: list[CvSection] = Field(
        default_factory=lambda: list(CvSection),
        max_length=len(CvSection),
        description="Secciones que incluir; por defecto, todas. Una sección sin "
        "nada no sale. Los datos de contacto salen siempre.",
    )
    excluded_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=MAX_EXCLUDED_IDS,
        description="Elementos del perfil que dejar fuera dentro de las secciones "
        "incluidas: entradas, logros, habilidades o idiomas, por id. Un id que no "
        "es de tu perfil no tiene efecto.",
    )
