import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../../services/document.service";
import { invalidateAfterDocumentChange } from "./invalidate";

export function useRenameDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => documentService.rename(id, name),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
