import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

/** Si era la activa, el servidor vuelve a los usos gratuitos. */
export function useDeleteAiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: AiProvider) => aiService.deleteKey(provider),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: aiKeys.keys() }),
  });
}
