import { useQuery } from "@tanstack/react-query";
import { healthKeys } from "../../health.keys";
import { healthService } from "../../services/health.service";

export function useHealth() {
  return useQuery({
    queryKey: healthKeys.all,
    queryFn: healthService.get,
    staleTime: 0,
  });
}
