import { applicationKeys } from "@/features/applications/application.keys";
import type { BoardFilters } from "./services/board.service";

// Bajo `applicationKeys.all`: cualquier cambio en una solicitud (que ya invalida
// esa raíz) refresca también el tablero.
export const boardKeys = {
  all: () => [...applicationKeys.all, "board"] as const,
  board: (filters: BoardFilters) => [...boardKeys.all(), filters] as const,
};
