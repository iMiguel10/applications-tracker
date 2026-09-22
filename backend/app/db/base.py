from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres deterministas para todas las constraints. Sin esto, Postgres inventa
# los nombres y Alembic no puede referenciarlas en un downgrade o al modificarlas.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Para todos los modelos: lee con RETURNING los valores que calcula la BD
    # también en los UPDATE (p. ej. updated_at con onupdate=clock_timestamp()).
    # Sin esto quedarían caducados tras el flush, y leerlos en async dispararía una
    # consulta implícita que falla (MissingGreenlet).
    # RUF012 se ignora: SQLAlchemy exige un dict de clase, y anotarlo como ClassVar
    # choca en mypy con la declaración de DeclarativeBase.
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012
