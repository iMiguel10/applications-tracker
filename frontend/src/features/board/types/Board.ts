import type {
  ApplicationStatus,
  CompanySummary,
} from "@/features/applications/types/Application";

/** Una tarjeta del tablero (RF-120): lo justo para pintarla. */
export interface BoardCard {
  id: string;
  position_title: string;
  company: CompanySummary;
  /** Desde cuándo está en su estado (último cambio de su historial). */
  status_since: string;
}

export interface BoardColumn {
  status: ApplicationStatus;
  /** Cuántas hay en el estado con los filtros, aunque `items` traiga solo las primeras 50. */
  total: number;
  items: BoardCard[];
  /** A qué estados se puede mover una tarjeta de esta columna (A8). */
  allowed_transitions: ApplicationStatus[];
}

/** `GET /applications/board`: una columna por estado, en el orden del proceso. */
export interface Board {
  columns: BoardColumn[];
}
