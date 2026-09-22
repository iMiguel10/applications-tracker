import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.application import (
    DEFAULT_CURRENCY,
    ApplicationOrigin,
    ApplicationSource,
    WorkMode,
)
from app.domain.application_status import ApplicationStatus
from app.schemas.common import (
    OptionalNotes,
    OptionalShortText,
    OptionalUrl,
    RequiredName,
    SortOrder,
)
from app.schemas.company import CompanySummary

Salary = Annotated[int, Field(ge=0, le=100_000_000)]


def _normalize_currency(value: Any) -> Any:
    return value.strip().upper() if isinstance(value, str) else value


# BeforeValidator y no StringConstraints(to_upper=True): Pydantic comprueba el
# `pattern` sobre el valor original, antes de to_upper, así que "eur" fallaría.
Currency = Annotated[
    str,
    BeforeValidator(_normalize_currency),
    StringConstraints(pattern="^[A-Z]{3}$"),
]
InitialStatus = Literal[ApplicationStatus.SAVED, ApplicationStatus.APPLIED]


class ApplicationCreate(BaseModel):
    company_id: uuid.UUID = Field(
        description="Empresa del usuario. Si no existe, se crea antes con POST /companies."
    )
    position_title: RequiredName = Field(examples=["Backend Developer"])
    job_url: OptionalUrl = Field(
        default=None, examples=["https://acme.example/jobs/42"]
    )
    location: OptionalShortText = Field(default=None, examples=["Madrid"])
    work_mode: WorkMode | None = None
    source: ApplicationSource | None = None
    status: InitialStatus = Field(
        default=ApplicationStatus.APPLIED,
        description="Estado inicial: `saved` (aún sin enviar) o `applied`. Los "
        "cambios posteriores de estado tienen su propia operación (F3).",
    )
    applied_at: date | None = Field(
        default=None,
        description="Fecha de envío. Si el estado es `applied` y no se indica, se "
        "usa la fecha de hoy (UTC).",
    )
    salary_min: Salary | None = Field(default=None, description="Bruto anual.")
    salary_max: Salary | None = Field(default=None, description="Bruto anual.")
    salary_currency: Currency = Field(
        default=DEFAULT_CURRENCY, description="Código ISO 4217.", examples=["EUR"]
    )
    notes: OptionalNotes = Field(default=None, description="Máximo 5 000 caracteres.")

    @model_validator(mode="after")
    def _salary_range(self) -> Self:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot be greater than salary_max")
        return self


class ApplicationUpdate(BaseModel):
    """Actualización parcial: solo se modifican los campos enviados; `null` vacía un
    campo opcional. El estado NO se cambia aquí (invariante 3)."""

    company_id: uuid.UUID | None = None
    position_title: RequiredName | None = None
    job_url: OptionalUrl = None
    location: OptionalShortText = None
    work_mode: WorkMode | None = None
    source: ApplicationSource | None = None
    applied_at: date | None = None
    salary_min: Salary | None = None
    salary_max: Salary | None = None
    salary_currency: Currency | None = None
    notes: OptionalNotes = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: CompanySummary
    position_title: str = Field(examples=["Backend Developer"])
    job_url: str | None
    location: str | None
    work_mode: WorkMode | None
    source: ApplicationSource | None
    origin: ApplicationOrigin
    status: ApplicationStatus
    applied_at: date | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    notes: str | None
    archived_at: datetime | None = Field(description="`null` si está activa.")
    last_activity_at: datetime = Field(
        description="Último cambio de estado o de entrevistas (no de datos)."
    )
    created_at: datetime
    updated_at: datetime


ArchivedFilter = Literal["active", "archived", "all"]
ApplicationSortField = Literal[
    "applied_at", "created_at", "updated_at", "company", "position_title"
]


class ApplicationListQuery(BaseModel):
    """Filtros del listado (RF-22). Los parámetros de lista se repiten:
    `?status=applied&status=screening`."""

    page: int = Field(default=1, ge=1, description="Página, empezando en 1.")
    limit: int = Field(default=20, ge=1, le=100, description="Elementos por página.")
    status: list[ApplicationStatus] = Field(default_factory=list)
    company_id: uuid.UUID | None = None
    work_mode: list[WorkMode] = Field(default_factory=list)
    source: list[ApplicationSource] = Field(default_factory=list)
    applied_from: date | None = Field(default=None, description="Fecha de envío desde.")
    applied_to: date | None = Field(default=None, description="Fecha de envío hasta.")
    q: str | None = Field(
        default=None, max_length=200, description="Busca en el puesto y la empresa."
    )
    archived: ArchivedFilter = Field(
        default="active", description="`active` (por defecto), `archived` o `all`."
    )
    sort_by: ApplicationSortField = Field(
        default="applied_at",
        description="Las solicitudes sin fecha de envío van siempre al final.",
    )
    order: SortOrder = "desc"

    @model_validator(mode="after")
    def _date_range(self) -> Self:
        if (
            self.applied_from
            and self.applied_to
            and self.applied_from > self.applied_to
        ):
            raise ValueError("applied_from cannot be after applied_to")
        return self
