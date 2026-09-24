from supertokens_python.asyncio import delete_user, get_user
from supertokens_python.recipe.emailpassword.asyncio import create_reset_password_link


class IdentityRepository:
    """Acceso a los datos de identidad que guarda SuperTokens (el almacén de identidades).

    Es el único punto del código que consulta usuarios al SDK, para que el resto
    no dependa de él y los tests puedan sustituirlo sin red.
    """

    async def get_email(self, supertokens_user_id: str) -> str | None:
        user = await get_user(supertokens_user_id)
        if user is None or not user.emails:
            return None
        return user.emails[0]

    async def create_password_reset_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        """Genera un token de recuperación en el core y devuelve el enlace a la
        página del frontend (WEBSITE_DOMAIN + /reset-password?token=…&tenantId=…).
        None si el usuario ya no existe."""
        link = await create_reset_password_link(tenant_id, supertokens_user_id, email)
        return link if isinstance(link, str) else None

    async def delete(self, supertokens_user_id: str) -> None:
        """Borra la identidad y sus sesiones en el core (credenciales incluidas)."""
        await delete_user(supertokens_user_id)
