/**
 * Lo que React Router pinta en la primera carga mientras resuelve los loaders
 * (p. ej. la comprobación de sesión). La comprobación es casi instantánea, así que
 * no se muestra nada en lugar de un spinner que parpadearía.
 */
export function PageFallback() {
  return null;
}
