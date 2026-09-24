import { apiClient } from "@/shared/lib/apiClient";
import type { Meta } from "../types/Meta";

export const metaService = {
  get: () => apiClient.get<Meta>("/meta"),
};
