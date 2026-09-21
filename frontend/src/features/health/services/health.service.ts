import { apiClient } from "@/shared/lib/apiClient";
import type { Health } from "../types/Health";

export const healthService = {
  get: () => apiClient.get<Health>("/health"),
};
