import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../../services/document.service";
import type { CvGenerateInput } from "../../types/Document";
import { invalidateAfterDocumentChange } from "./invalidate";

export function useGenerateCv() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CvGenerateInput) => documentService.generate(input),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
