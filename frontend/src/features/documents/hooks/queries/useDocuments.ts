import { useQuery } from "@tanstack/react-query";
import { documentKeys } from "../../document.keys";
import { documentService } from "../../services/document.service";
import type { DocumentListParams } from "../../types/Document";

export function useDocuments(params: DocumentListParams) {
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => documentService.list(params),
  });
}
