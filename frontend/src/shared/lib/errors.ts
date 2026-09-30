import i18n from "@/shared/i18n/i18n";
import { ApiError } from "./apiClient";
import { formatBytes } from "./format";
import { formatRetryAfter } from "./retryAfter";

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
  if (!(error instanceof ApiError)) return {};
  // 429 (RNF-04): el mensaje dice cuánto esperar, en palabras.
  const retryAfter = error.params.retry_after;
  if (error.code === "rate_limited" && typeof retryAfter === "number") {
    return { ...error.params, wait: formatRetryAfter(retryAfter, i18n.language) };
  }
  // Tamaños en bytes: el mensaje los dice en MB.
  const bytes = (value: unknown) =>
    typeof value === "number" ? formatBytes(value, i18n.language) : value;
  if (error.code === "file_too_large") {
    return { ...error.params, max: bytes(error.params.max_bytes) };
  }
  if (error.code === "storage_limit_reached") {
    return { ...error.params, limit: bytes(error.params.limit), used: bytes(error.params.used) };
  }
  return error.params;
}
