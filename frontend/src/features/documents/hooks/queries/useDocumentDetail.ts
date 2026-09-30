import { useQuery } from "@tanstack/react-query";
import { documentKeys } from "../../document.keys";
import { documentService } from "../../services/document.service";

/** El documento y dónde se envió (RF-92). Solo con un id: el visor cerrado no pide nada. */
export function useDocumentDetail(id: string | null) {
  return useQuery({
    queryKey: documentKeys.detail(id ?? ""),
    queryFn: () => documentService.get(id!),
    enabled: id !== null,
  });
}
