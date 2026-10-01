import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usageKeys } from "@/features/usage/usage.keys";
import { documentKeys } from "../../document.keys";
import { documentService } from "../../services/document.service";
import type { DocumentListParams } from "../../types/Document";

/** Cada cuánto se consulta la biblioteca mientras algún CV se está generando (A35). */
export const PENDING_POLL_MS = 2000;

export function useDocuments(params: DocumentListParams) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => documentService.list(params),
    // El estado de un CV generado vive en su fila: mientras alguno esté
    // `pending`, se vuelve a pedir la página hasta que termine.
    refetchInterval: (current) =>
      current.state.data?.items.some((document) => document.status === "pending")
        ? PENDING_POLL_MS
        : false,
  });

  // Al terminar un CV, su PDF pasa a ocupar almacenamiento: el uso de la cuenta
  // (RF-141) cambia sin que el usuario haya hecho nada.
  const pending = query.data?.items.filter((document) => document.status === "pending").length;
  const previous = useRef(pending);
  useEffect(() => {
    if (previous.current && pending !== undefined && pending < previous.current) {
      void queryClient.invalidateQueries({ queryKey: usageKeys.all });
    }
    previous.current = pending;
  }, [pending, queryClient]);

  return query;
}
