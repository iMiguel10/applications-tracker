import type { QueryClient } from "@tanstack/react-query";
import { usageKeys } from "@/features/usage/usage.keys";
import { documentKeys } from "../../document.keys";

/** Subir o borrar un documento cambia también el uso de la cuenta (documentos y
 * almacenamiento). */
export function invalidateAfterDocumentChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: documentKeys.all });
  queryClient.invalidateQueries({ queryKey: usageKeys.all });
}
