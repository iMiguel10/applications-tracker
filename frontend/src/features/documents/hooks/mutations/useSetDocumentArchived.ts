import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../../services/document.service";
import { invalidateAfterDocumentChange } from "./invalidate";

export function useSetDocumentArchived() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      documentService.setArchived(id, archived),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
