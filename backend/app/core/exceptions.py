class AppException(Exception):
    """Error de negocio con un `code` estable que el frontend traduce (errors.<code>).

    La respuesta HTTP es {"detail": message, "code": code}. El texto de `message`
    es para humanos y puede cambiar; `code` es parte del contrato de la API.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "bad_request",
        extra: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        # Datos para el cliente además de detail y code (p. ej. limit y used de un
        # límite alcanzado, RF-142). Se añaden tal cual a la respuesta.
        self.extra = extra or {}
        self.headers = headers or {}
        super().__init__(message)


class NotFoundError(AppException):
    """404. También para recursos de otro usuario: no se distingue (decisión A10)."""

    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", status_code=404, code="not_found")


class ConflictError(AppException):
    """409: la petición es válida pero una regla de negocio la impide."""

    def __init__(self, message: str, code: str):
        super().__init__(message, status_code=409, code=code)


class LimitReachedError(AppException):
    """409: se ha alcanzado una cuota (especificación §10). Dice cuál y cuánto
    (RF-142): `{"detail", "code", "limit", "used"}`."""

    def __init__(self, code: str, *, limit: int, used: int):
        super().__init__(
            f"Limit reached: {used} of {limit}",
            status_code=409,
            code=code,
            extra={"limit": limit, "used": used},
        )


class RateLimitedError(AppException):
    """429 (RNF-04): demasiadas peticiones. `retry_after` en el cuerpo y en la
    cabecera `Retry-After`, en segundos, para que el cliente diga cuánto esperar."""

    def __init__(self, retry_after: int):
        super().__init__(
            "Too many requests",
            status_code=429,
            code="rate_limited",
            extra={"retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )
