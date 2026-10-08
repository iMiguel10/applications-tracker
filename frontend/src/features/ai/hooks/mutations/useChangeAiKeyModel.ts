import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

export function useChangeAiKeyModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ provider, model }: { provider: AiProvider; model: string }) =>
      aiService.changeKeyModel(provider, model),
    onSuccess: (keys) => queryClient.setQueryData(aiKeys.keys(), keys),
  });
}
