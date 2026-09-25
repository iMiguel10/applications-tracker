from pydantic import BaseModel, ConfigDict, Field

from app.domain.limits import LimitKey


class LimitUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: LimitKey = Field(description="Qué se limita.")
    used: int = Field(description="Consumo actual, contado sobre los datos reales.")
    limit: int | None = Field(
        description="Límite de esta cuenta: el global de la instalación o una "
        "excepción individual. `null`: esta cuenta no tiene límite en este recurso."
    )
    remaining: int | None = Field(
        description="`limit - used`, nunca negativo. `null` si no hay límite."
    )
    renews: bool = Field(
        description="Si el consumo vuelve a cero cada cierto tiempo. Ningún límite "
        "actual se renueva."
    )


class UsageRead(BaseModel):
    limits: list[LimitUsageRead]
    warning_ratio: float = Field(
        description="A partir de esta fracción de un límite (`used / limit`) la "
        "aplicación avisa antes de llegar al tope (RF-144).",
        examples=[0.8],
    )
