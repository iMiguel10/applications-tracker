import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invalidateAfterDocumentChange } from "@/features/documents/hooks/mutations/invalidate";
import { aiService, type AiDocumentInput } from "../../services/ai.service";

/** El PDF de una propuesta revisada: el CV adaptado o la carta (RF-113, RF-114). */
export function useCreateAiDocument(applicationId: string, proposalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AiDocumentInput) =>
      aiService.createDocument(applicationId, proposalId, input),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
