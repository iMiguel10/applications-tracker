import { useMutation, useQueryClient } from "@tanstack/react-query";
import { usageKeys } from "@/features/usage/usage.keys";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import type { AiTask, ProposalLanguage } from "../../types/Ai";

export function useRequestAiProposal(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, language }: { kind: AiTask; language: ProposalLanguage }) =>
      aiService.requestProposal(applicationId, kind, language),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: aiKeys.proposals(applicationId) });
      // La que está en cola ya cuenta para el uso gratuito.
      void queryClient.invalidateQueries({ queryKey: usageKeys.all });
    },
  });
}
