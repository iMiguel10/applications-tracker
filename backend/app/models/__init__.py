# Importar aquí cada modelo: es lo que los registra en Base.metadata, y
# migrations/env.py importa este paquete para que Alembic los vea.
from app.models.application import Application

__all__ = ["Application"]
