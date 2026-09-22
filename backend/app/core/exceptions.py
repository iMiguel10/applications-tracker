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
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    """404. También para recursos de otro usuario: no se distingue (decisión A10)."""

    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", status_code=404, code="not_found")


class ConflictError(AppException):
    """409: la petición es válida pero una regla de negocio la impide."""

    def __init__(self, message: str, code: str):
        super().__init__(message, status_code=409, code=code)


class LimitReachedError(ConflictError):
    """409: se ha alcanzado una cuota (especificación §10)."""

    def __init__(self, resource: str, limit: int):
        super().__init__(
            f"Limit of {limit} {resource} reached", code=f"{resource}_limit_reached"
        )
