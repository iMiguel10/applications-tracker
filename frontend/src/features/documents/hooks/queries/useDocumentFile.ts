import { useQuery } from "@tanstack/react-query";
import { documentKeys } from "../../document.keys";
import { documentService } from "../../services/document.service";

/** El PDF de un documento, para el visor. Solo mientras está abierto: no se
 * guarda en caché al cerrarlo (un CV no tiene por qué quedarse en memoria). */
export function useDocumentFile(id: string | null) {
  return useQuery({
    queryKey: documentKeys.file(id ?? ""),
    queryFn: () => documentService.file(id!),
    enabled: id !== null,
    gcTime: 0,
  });
}
