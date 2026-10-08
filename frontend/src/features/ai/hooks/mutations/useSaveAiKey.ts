import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiProvider } from "../../types/Ai";

/** Guarda (o sustituye) la clave de un proveedor; el servidor la comprueba antes y
 * la deja activa. */
export function useSaveAiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      provider,
      apiKey,
      model,
    }: {
      provider: AiProvider;
      apiKey: string;
      model: string | null;
    }) => aiService.saveKey(provider, apiKey, model),
    onSuccess: (keys) => queryClient.setQueryData(aiKeys.keys(), keys),
  });
}
