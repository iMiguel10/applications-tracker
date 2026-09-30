import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../../services/document.service";
import { invalidateAfterDocumentChange } from "./invalidate";

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: documentService.remove,
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
