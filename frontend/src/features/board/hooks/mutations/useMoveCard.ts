import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invalidateAfterApplicationChange } from "@/features/applications/hooks/mutations/invalidate";
import { applicationStatusChangeService } from "@/features/applications/services/applicationStatusChange.service";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import { boardKeys } from "../../board.keys";
import { moveCard } from "../../lib/board";
import type { BoardFilters } from "../../services/board.service";
import type { Board } from "../../types/Board";

export interface MoveCardInput {
  cardId: string;
  from: ApplicationStatus;
  to: ApplicationStatus;
}

/**
 * Soltar una tarjeta en otra columna (RF-121): el cambio de estado de siempre,
 * con fecha "ahora" y sin nota (decisión 0014). La tarjeta se pinta en su nueva
 * columna al momento y vuelve a la suya si la API lo rechaza.
 */
export function useMoveCard(filters: BoardFilters) {
  const queryClient = useQueryClient();
  const key = boardKeys.board(filters);

  return useMutation({
    mutationFn: ({ cardId, to }: MoveCardInput) =>
      applicationStatusChangeService.create(cardId, {
        to_status: to,
        changed_at: null,
        note: "",
      }),
    onMutate: async ({ cardId, from, to }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<Board>(key);
      if (previous)
        queryClient.setQueryData(key, moveCard(previous, cardId, from, to));
      return { previous };
    },
    onError: (_error, _input, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
    },
    onSettled: () => invalidateAfterApplicationChange(queryClient),
  });
}
