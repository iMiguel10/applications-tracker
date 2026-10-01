import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { ApplicationListParams } from "@/features/applications/types/Application";
import type { Board } from "../types/Board";

/** Solo los filtros del listado (RF-122): el tablero no pagina, no ordena y nunca
 * muestra archivadas. */
export function boardFilters(params: ApplicationListParams) {
  return {
    status: params.status,
    company_id: params.company_id,
    work_mode: params.work_mode,
    source: params.source,
    applied_from: params.applied_from,
    applied_to: params.applied_to,
    q: params.q || null,
  };
}

export type BoardFilters = ReturnType<typeof boardFilters>;

export const boardService = {
  get: (filters: BoardFilters) =>
    apiClient.get<Board>(`/applications/board${toQueryString(filters)}`),
};
