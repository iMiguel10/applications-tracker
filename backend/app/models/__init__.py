# Importar aquí cada modelo: es lo que los registra en Base.metadata, y
# migrations/env.py importa este paquete para que Alembic los vea.
from app.models.application import Application
from app.models.user import User

__all__ = ["Application", "User"]
