import { apiClient } from "@/shared/lib/apiClient";
import type { Dashboard } from "../types/Dashboard";

export const dashboardService = {
  get: () => apiClient.get<Dashboard>("/dashboard"),
};
