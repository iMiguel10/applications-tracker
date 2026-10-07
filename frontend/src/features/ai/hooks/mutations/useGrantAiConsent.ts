import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

export function useGrantAiConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: AiProvider) => aiService.grantConsent(provider),
    onSuccess: (consents) => queryClient.setQueryData(aiKeys.consents(), consents),
  });
}
