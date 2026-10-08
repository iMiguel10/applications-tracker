import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

/** Con qué se usa la IA: una clave guardada o, con null, los usos gratuitos. */
export function useSetActiveAiProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: AiProvider | null) => aiService.setActiveProvider(provider),
    onSuccess: (keys) => queryClient.setQueryData(aiKeys.keys(), keys),
  });
}
