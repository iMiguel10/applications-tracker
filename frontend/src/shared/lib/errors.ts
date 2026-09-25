import i18n from "@/shared/i18n/i18n";
import { ApiError } from "./apiClient";

/**
 * Clave de i18n para un error de la API. Se traduce por el `code` estable
 * (errors.<code>), nunca por el texto de `detail`, que es informativo y puede
 * cambiar. Un código sin traducción cae en errors.generic.
 */
export function errorMessageKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code && i18n.exists(`errors.${error.code}`)) return `errors.${error.code}`;
    if (error.status === 422) return "errors.validation";
  }
  return "errors.generic";
}

/** Valores para interpolar en el mensaje de `errorMessageKey` (p. ej. el límite
 * alcanzado). Se usa siempre en pareja: `t(errorMessageKey(e), errorMessageParams(e))`. */
export function errorMessageParams(error: unknown): Record<string, unknown> {
  return error instanceof ApiError ? error.params : {};
}
