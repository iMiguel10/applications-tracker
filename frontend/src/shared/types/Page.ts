/** Respuesta paginada común a todos los listados de la API. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}
