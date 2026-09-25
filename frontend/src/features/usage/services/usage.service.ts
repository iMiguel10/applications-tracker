import { apiClient } from "@/shared/lib/apiClient";
import type { Usage } from "../types/Usage";

export const usageService = {
  get: () => apiClient.get<Usage>("/me/usage"),
};
