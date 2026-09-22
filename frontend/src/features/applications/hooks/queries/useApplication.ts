import { useQuery } from "@tanstack/react-query";
import { applicationKeys } from "../../application.keys";
import { applicationService } from "../../services/application.service";

export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => applicationService.get(id),
  });
}
