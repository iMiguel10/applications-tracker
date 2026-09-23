import { useQuery } from "@tanstack/react-query";
import { applicationKeys } from "../../application.keys";
import { applicationStatusChangeService } from "../../services/applicationStatusChange.service";

export function useApplicationStatusChanges(applicationId: string) {
  return useQuery({
    queryKey: applicationKeys.history(applicationId),
    queryFn: () => applicationStatusChangeService.list(applicationId),
  });
}
