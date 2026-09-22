import type { QueryClient } from "@tanstack/react-query";
import { companyKeys } from "@/features/companies/company.keys";
import { applicationKeys } from "../../application.keys";

/**
 * Tras cualquier cambio en una solicitud: listados, detalle y el recuento de
 * solicitudes de las empresas (applications_count).
 */
export function invalidateAfterApplicationChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: applicationKeys.all });
  queryClient.invalidateQueries({ queryKey: companyKeys.all });
}
