import type { QueryClient } from "@tanstack/react-query";
import { companyKeys } from "@/features/companies/company.keys";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { applicationKeys } from "../../application.keys";

/**
 * Tras cualquier cambio en una solicitud: listados, detalle, el recuento de
 * solicitudes de las empresas (applications_count) y el dashboard (F5), que
 * agrega sobre las mismas solicitudes.
 */
export function invalidateAfterApplicationChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: applicationKeys.all });
  queryClient.invalidateQueries({ queryKey: companyKeys.all });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
}
