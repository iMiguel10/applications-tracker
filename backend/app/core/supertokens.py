from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.recipe import emailpassword, session

from app.core.config import settings


def init_supertokens() -> None:
    """Inicializa el SDK. Debe llamarse antes de crear la app de FastAPI.

    Ver docs/arquitectura/autenticacion.md: sesiones por cookies httpOnly y
    receta email + contraseña. El core solo es accesible por la red interna.
    """
    init(
        app_info=InputAppInfo(
            app_name="Applications Tracker",
            api_domain=settings.api_domain,
            website_domain=settings.website_domain,
            api_base_path="/auth",
            website_base_path="/auth",
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=settings.supertokens_connection_uri,
            api_key=settings.supertokens_api_key,
        ),
        framework="fastapi",
        recipe_list=[
            # Cookies y cabeceras (decisión 0003). El frontend usa cookies httpOnly
            # (modo por defecto de supertokens-web-js) y nunca ve los tokens. Un
            # cliente que envíe `st-auth-mode: header` en el login los recibe en
            # cabeceras y se autentica con `Authorization: Bearer` (integraciones,
            # Swagger).
            session.init(),
            emailpassword.init(),
        ],
        mode="asgi",
        # Sin envío de datos de uso a SuperTokens.
        telemetry=False,
    )
