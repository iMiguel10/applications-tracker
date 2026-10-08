import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

/** Retira el consentimiento (RF-116): desde ahora no se envía nada a ese proveedor. */
export function useRevokeAiConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: AiProvider) => aiService.revokeConsent(provider),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: aiKeys.consents() }),
  });
}
