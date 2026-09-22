const DEFAULT_REDIRECT = "/applications";

/**
 * Destino tras el login a partir de ?redirect=. Solo se aceptan rutas internas:
 * "/..." pero no "//..." (URL de otro dominio relativa al protocolo) ni "/\..."
 * (algunos navegadores la tratan igual). Evita un open redirect: un enlace
 * /login?redirect=https://malo.example llevaría al usuario, recién autenticado,
 * a una web externa.
 */
export function safeRedirect(redirect: string | null | undefined): string {
  if (
    !redirect ||
    !redirect.startsWith("/") ||
    redirect.startsWith("//") ||
    redirect.startsWith("/\\")
  ) {
    return DEFAULT_REDIRECT;
  }
  return redirect;
}
