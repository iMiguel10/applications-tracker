from pydantic import BaseModel, Field


class HealthRead(BaseModel):
    status: str = Field(description="`ok` si la API responde.", examples=["ok"])
    database: str = Field(
        description="`ok` si la base de datos responde.", examples=["ok"]
    )
    environment: str = Field(
        description="Entorno en el que corre la API.", examples=["development"]
    )
