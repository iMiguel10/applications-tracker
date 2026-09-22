LIKE_ESCAPE = "\\"


def contains_pattern(term: str) -> str:
    """Patrón ILIKE "contiene", escapando los comodines que escriba el usuario.

    Sin escapar, buscar "100%" o "dev_ops" trataría % y _ como comodines de SQL:
    "dev_ops" encontraría también "dev-ops" y "devXops". Usar siempre con
    `.ilike(contains_pattern(term), escape=LIKE_ESCAPE)`.
    """
    escaped = (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )
    return f"%{escaped}%"
