from supertokens_python.asyncio import (
    delete_user,
    get_user,
    list_users_by_account_info,
)
from supertokens_python.recipe.emailpassword.asyncio import (
    create_reset_password_link,
    sign_up,
    update_email_or_password,
    verify_credentials,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    PasswordPolicyViolationError,
    SignInOkResult,
    SignUpOkResult,
    UpdateEmailOrPasswordOkResult,
)
from supertokens_python.recipe.emailverification.asyncio import (
    create_email_verification_link,
    create_email_verification_token,
    is_email_verified,
    verify_email_using_token,
)
from supertokens_python.recipe.emailverification.interfaces import (
    CreateEmailVerificationLinkOkResult,
    CreateEmailVerificationTokenOkResult,
)
from supertokens_python.recipe.session.asyncio import (
    get_all_session_handles_for_user,
    revoke_multiple_sessions,
)
from supertokens_python.types import RecipeUserId
from supertokens_python.types.base import AccountInfoInput


class IdentityRepository:
    """Acceso a los datos de identidad que guarda SuperTokens (el almacén de identidades).

    Es el único punto del código que consulta usuarios al SDK, para que el resto
    no dependa de él y los tests puedan sustituirlo sin red.

    Sin account linking (no se activa), cada usuario tiene un solo método de acceso
    y su "recipe user id" es su propio id: por eso se construye con el mismo valor.
    """

    async def get_email(self, supertokens_user_id: str) -> str | None:
        user = await get_user(supertokens_user_id)
        if user is None or not user.emails:
            return None
        return user.emails[0]

    async def find_id_by_email(self, email: str) -> str | None:
        """Para los scripts de administración, que parten de un email."""
        users = await list_users_by_account_info(
            "public", AccountInfoInput(email=email)
        )
        return users[0].id if users else None

    async def create_account(self, email: str, password: str) -> str | None:
        """Crea una identidad de email y contraseña, también con el registro cerrado
        (`SIGNUP_ENABLED=false`): llama a la receta, no a la ruta `/auth/signup`,
        así que ni pasa por su override ni encola el email de verificación. Para
        `scripts/create_user.py` (decisión 0022). None si el email ya existe."""
        result = await sign_up("public", email, password)
        return result.user.id if isinstance(result, SignUpOkResult) else None

    async def mark_email_verified(self, supertokens_user_id: str, email: str) -> None:
        """Da el email por verificado sin enviar nada: lo da por bueno quien
        administra al crear la cuenta."""
        token = await create_email_verification_token(
            "public", RecipeUserId(supertokens_user_id), email
        )
        if isinstance(token, CreateEmailVerificationTokenOkResult):
            await verify_email_using_token("public", token.token)

    async def create_password_reset_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        """Genera un token de recuperación en el core y devuelve el enlace a la
        página del frontend (WEBSITE_DOMAIN + /reset-password?token=…&tenantId=…).
        None si el usuario ya no existe."""
        link = await create_reset_password_link(tenant_id, supertokens_user_id, email)
        return link if isinstance(link, str) else None

    async def create_email_verification_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        """Enlace de verificación (WEBSITE_DOMAIN + /verify-email?token=…&tenantId=…).
        None si el email ya está verificado."""
        result = await create_email_verification_link(
            tenant_id, RecipeUserId(supertokens_user_id), email
        )
        if isinstance(result, CreateEmailVerificationLinkOkResult):
            return result.link
        return None

    async def verify_password(
        self, supertokens_user_id: str, email: str, password: str
    ) -> bool:
        """Si `password` es la contraseña de esa cuenta. Pregunta al core sin crear
        sesión; se exige además que la identidad sea la misma, no otra con el
        mismo email."""
        result = await verify_credentials("public", email, password)
        return isinstance(result, SignInOkResult) and result.user.id == (
            supertokens_user_id
        )

    async def update_password(self, supertokens_user_id: str, password: str) -> bool:
        """Cambia la contraseña aplicando la política del backend (invariante 7).
        False si no la cumple; no cambia nada."""
        result = await update_email_or_password(
            RecipeUserId(supertokens_user_id),
            password=password,
            apply_password_policy=True,
            tenant_id_for_password_policy="public",
        )
        if isinstance(result, UpdateEmailOrPasswordOkResult):
            return True
        if isinstance(result, PasswordPolicyViolationError):
            return False
        # La cuenta desapareció entre la comprobación y el cambio (un borrado de
        # cuenta simultáneo). El resto de resultados son de cambiar el email.
        raise RuntimeError(f"No se pudo cambiar la contraseña: {type(result).__name__}")

    async def revoke_other_sessions(
        self, supertokens_user_id: str, keep_session_handle: str
    ) -> None:
        """Cierra todas las sesiones de la cuenta salvo `keep_session_handle`: sus
        refresh tokens dejan de servir. Un access token ya emitido sigue valiendo
        hasta caducar (5 min, decisión 0002)."""
        handles = await get_all_session_handles_for_user(supertokens_user_id)
        others = [handle for handle in handles if handle != keep_session_handle]
        if others:
            await revoke_multiple_sessions(others)

    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        """Consulta al core, no al access token (autenticación §8)."""
        return await is_email_verified(RecipeUserId(supertokens_user_id))

    async def delete(self, supertokens_user_id: str) -> None:
        """Borra la identidad y sus sesiones en el core (credenciales incluidas)."""
        await delete_user(supertokens_user_id)
