export type QueryValue = string | number | boolean | null | undefined;

/**
 * Query string para la API. Las listas se envían como parámetros repetidos
 * (`status=applied&status=screening`), que es lo que espera FastAPI; los valores
 * vacíos se omiten.
 */
export function toQueryString(params: Record<string, QueryValue | QueryValue[]>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== null && item !== undefined && item !== "") {
        search.append(key, String(item));
      }
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
