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


def retry_after_headers(retry_after: int) -> dict[str, str]:
    """Cabeceras de un 429. `Retry-After` se expone aquí, en la propia respuesta, y
    no con `expose_headers` en el `CORSMiddleware`: con esa opción, Starlette
    sobrescribe en TODAS las respuestas el `Access-Control-Expose-Headers` que pone
    SuperTokens, el navegador deja de poder leer `front-token` y el inicio de sesión
    no crea sesión (roto así en F11 hasta el cierre de la fase)."""
    return {
        "Retry-After": str(retry_after),
        "Access-Control-Expose-Headers": "Retry-After",
    }


class RateLimitedError(AppException):
    """429 (RNF-04): demasiadas peticiones. `retry_after` en el cuerpo y en la
    cabecera `Retry-After`, en segundos, para que el cliente diga cuánto esperar."""

    def __init__(self, retry_after: int):
        super().__init__(
            "Too many requests",
            status_code=429,
            code="rate_limited",
            extra={"retry_after": retry_after},
            headers=retry_after_headers(retry_after),
        )


class FileTooLargeAppError(AppException):
    """413: el fichero pasa del tamaño máximo (especificación §10). Se corta al
    leerlo, sin esperar al final."""

    def __init__(self, max_bytes: int):
        super().__init__(
            "File too large",
            status_code=413,
            code="file_too_large",
            extra={"max_bytes": max_bytes},
        )


class InvalidFileTypeError(AppException):
    """422: el contenido no es un PDF válido, diga lo que diga la extensión."""

    def __init__(self) -> None:
        super().__init__("Not a valid PDF", status_code=422, code="invalid_file_type")
