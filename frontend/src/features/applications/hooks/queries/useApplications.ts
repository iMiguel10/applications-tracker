import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { applicationKeys } from "../../application.keys";
import { applicationService } from "../../services/application.service";
import type { ApplicationListParams } from "../../types/Application";

export function useApplications(params: ApplicationListParams) {
  return useQuery({
    queryKey: applicationKeys.list(params),
    queryFn: () => applicationService.list(params),
    // Al cambiar de página se mantiene la anterior visible hasta que llega la nueva.
    placeholderData: keepPreviousData,
  });
}
