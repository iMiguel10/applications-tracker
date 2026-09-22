from enum import StrEnum

from sqlalchemy import CheckConstraint


def enum_check(column: str, enum: type[StrEnum], name: str) -> CheckConstraint:
    """CHECK (column IN (...)) generado desde un StrEnum de domain/.

    La lista de valores válidos se escribe una sola vez (el enum) y la BD la aplica
    igual. Decisión A5: varchar + CHECK en lugar de enum nativo de Postgres. Si el
    enum cambia, autogenerate NO detecta el cambio del CHECK: hay que escribir la
    migración a mano (drop + create de la constraint).
    """
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name)
