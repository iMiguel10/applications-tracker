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
            # Solo cookies: el frontend nunca maneja tokens (RNF-01).
            session.init(get_token_transfer_method=lambda *_: "cookie"),
            emailpassword.init(),
        ],
        mode="asgi",
        # Sin envío de datos de uso a SuperTokens.
        telemetry=False,
    )
