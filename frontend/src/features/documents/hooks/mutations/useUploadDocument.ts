import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../../services/document.service";
import type { DocumentKind } from "../../types/Document";
import { invalidateAfterDocumentChange } from "./invalidate";

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ kind, file }: { kind: DocumentKind; file: File }) =>
      documentService.upload(kind, file),
    onSuccess: () => invalidateAfterDocumentChange(queryClient),
  });
}
