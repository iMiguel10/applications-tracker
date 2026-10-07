import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invalidateAfterDocumentChange } from "@/features/documents/hooks/mutations/invalidate";
import { aiService } from "../../services/ai.service";
import type { ReviewedCvProposal } from "../../types/Ai";

export function useCreateTailoredCv(applicationId: string, proposalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { design: string; name: string | null; proposal: ReviewedCvProposal }) =>
      aiService.createDocument(applicationId, proposalId, input),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
