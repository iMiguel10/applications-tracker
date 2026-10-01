import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { boardKeys } from "../../board.keys";
import { boardService, type BoardFilters } from "../../services/board.service";

export function useBoard(filters: BoardFilters, { enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: boardKeys.board(filters),
    queryFn: () => boardService.get(filters),
    // Al cambiar un filtro se mantiene el tablero anterior hasta que llega el nuevo.
    placeholderData: keepPreviousData,
    enabled,
  });
}
