from supertokens_python.asyncio import delete_user, get_user


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

    async def delete(self, supertokens_user_id: str) -> None:
        """Borra la identidad y sus sesiones en el core (credenciales incluidas)."""
        await delete_user(supertokens_user_id)
