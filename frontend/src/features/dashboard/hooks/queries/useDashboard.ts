import { useQuery } from "@tanstack/react-query";
import { dashboardKeys } from "../../dashboard.keys";
import { dashboardService } from "../../services/dashboard.service";

export function useDashboard() {
  return useQuery({
    queryKey: dashboardKeys.all,
    queryFn: dashboardService.get,
  });
}
